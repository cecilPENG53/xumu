#!/usr/bin/env python3
"""Talking-head voice editing: anchor keeps -> word-boundary EDL -> frame-exact cut -> per-character cue map.

  edl     keeps.json + transcripts/<source>.json  ->  edl_voice.json (+ readable check text with suspected stumbles)
  render  edl_voice.json                          ->  one frame-exact A/V file (concat *filter*, single encode)
  cues    edl_voice.json + transcripts            ->  cue_chars.json + sections.json (cut-timeline seconds)
  listen  edl_voice.json + rendered cut           ->  short context clips around edits and suspects, one compilation

Transcripts use the ElevenLabs Scribe layout that Video Use writes: {"words": [{"text", "start", "end", "type"}]}.

keeps.json:
  {"sources": {"<name>": "<media path>"},
   "sections": [{"id": "B01", "source": "<name>",
                 "keeps": [[start_anchor, end_anchor, force_start_s?, force_end_s?],
                           {"from": start_anchor, "to": end_anchor, "start": s?, "end": s?,
                            "drop": [[source_s, source_s], ...]}, ...]}]}
Anchors are substrings of the source transcript with spaces removed. Each keep is searched after the previous keep
of the same source, so repeated phrases resolve in reading order. force_* / start / end (seconds or null) override a
cut point when ASR timing merged a restart ("OPC，OPC") into one word. drop removes voiced material inside a keep
(a false start, a dragged syllable tail) that silence-based cutting cannot reach; its edges snap to the quietest
10 ms within 40 ms.

The edl report lists suspected stumbles (repeated starts, long syllables, fillers, mid-sentence pauses, sound the ASR
did not transcribe). They are listening targets, not verdicts.
"""
import argparse
from itertools import groupby
import json
from pathlib import Path
import re
import subprocess
import sys

SR_ANALYSIS = 16000   # analysis rate for cut refinement; 10 ms RMS frames
SR_OUT = 48000
MIN_PIECE = 0.08      # a kept sliver shorter than this between drops is discarded (it would only click)
FILLERS = {'嗯', '呃', '额', '唔', 'em', 'emm', 'uh', 'um', 'umm', 'er', 'erm'}
KIND_LABEL = {'repeat': '重复起音', 'long': '字音偏长', 'filler': '语气词', 'pause': '句内停顿',
              'noise': '未转录的声音', 'at': '指定时间'}
JOIN_LABEL = {'section': '换段', 'keep': '删句', 'drop': '删片段', 'pause': '缩停顿'}
WORD_CHAR = re.compile(r'[0-9A-Za-z㐀-鿿]')
END_PUNCT = tuple('，。！？、；：,.!?;:…')


def ffmpeg():
    return 'ffmpeg'


def load_words(transcripts, name):
    data = json.loads((transcripts / f'{name}.json').read_text(encoding='utf-8'))
    return [w for w in data['words'] if w.get('type', 'word') == 'word']


def flatten(words):
    """Concatenated transcript text without spaces, plus the word index owning each character."""
    text, owner = '', []
    for i, w in enumerate(words):
        piece = w['text'].replace(' ', '')
        text += piece
        owner += [i] * len(piece)
    return text, owner


def parse_keep(keep):
    """List form [from, to, force_start?, force_end?] or dict form with an optional drop list."""
    if isinstance(keep, dict):
        drops = [(float(d[0]), float(d[1])) for d in keep.get('drop', [])]
        return keep['from'], keep['to'], keep.get('start'), keep.get('end'), drops
    return keep[0], keep[1], keep[2] if len(keep) > 2 else None, keep[3] if len(keep) > 3 else None, []


def clock(t):
    return f'{int(t // 60):02d}:{t % 60:05.2f}'


class Audio:
    """Cached 16 kHz mono samples per source, used only to move cut points onto real silences."""

    def __init__(self, sources):
        self.sources, self.cache = sources, {}

    def samples(self, name):
        import numpy as np
        if name not in self.cache:
            raw = subprocess.run([ffmpeg(), '-loglevel', 'error', '-i', self.sources[name], '-vn', '-ac', '1',
                                  '-ar', str(SR_ANALYSIS), '-f', 's16le', '-'], capture_output=True, check=True).stdout
            self.cache[name] = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        return self.cache[name]

    def rms(self, name, t0, t1):
        import numpy as np
        a = self.samples(name)
        i0, i1 = max(0, int(t0 * SR_ANALYSIS)), max(0, int(t1 * SR_ANALYSIS))
        hop = SR_ANALYSIS // 100
        n = max(0, (i1 - i0) // hop)
        if n == 0:
            return np.zeros(0)
        return np.sqrt(np.mean(a[i0:i0 + n * hop].reshape(n, hop) ** 2, axis=1))

    def quiet_runs(self, name, t0, t1, frames=3):
        """(start, end) of silences of at least frames*10 ms inside [t0, t1]."""
        import numpy as np
        r = self.rms(name, t0, t1)
        if len(r) == 0:
            return []
        context = self.rms(name, t0 - 1.0, t1 + 1.0)
        threshold = max(250.0, 0.10 * float(np.percentile(context, 90))) if len(context) else 250.0
        quiet, runs, k = r < threshold, [], 0
        while k < len(quiet):
            if quiet[k]:
                j = k
                while j < len(quiet) and quiet[j]:
                    j += 1
                if j - k >= frames:
                    runs.append((t0 + k * 0.01, t0 + j * 0.01))
                k = j
            else:
                k += 1
        return runs

    def refine_end(self, name, last_word, end):
        """Cut before a leaked restart: first silence after the last kept syllable."""
        runs = self.quiet_runs(name, last_word['start'] + 0.12, end, frames=5)
        return min(end, runs[0][0] + 0.05) if runs else end

    def refine_start(self, name, start, first_word):
        """Trim only material before the first kept syllable; never cut into it."""
        runs = self.quiet_runs(name, start, first_word['start'] + 0.02, frames=6)
        return max(start, runs[-1][1] - 0.04) if runs else start

    def snap(self, name, t, radius=0.04):
        """Quietest 10 ms frame within +-radius: drop edges land between syllables, not inside one."""
        import numpy as np
        r = self.rms(name, t - radius, t + radius)
        return t - radius + 0.01 * int(np.argmin(r)) + 0.005 if len(r) else t

    def voiced_islands(self, name, t0, t1):
        quiet = self.quiet_runs(name, t0, t1, frames=3)
        islands, cursor = [], t0
        for q0, q1 in quiet:
            if q0 > cursor:
                islands.append((cursor, q0))
            cursor = max(cursor, q1)
        if cursor < t1:
            islands.append((cursor, t1))
        return islands


def split_silences(audio, src, spans, gap_max, pause_keep):
    """ASR often folds a pause into a word's timing, where word gaps cannot see it. Find long silences in the audio
    and shorten them like word-gap pauses; silence at a span edge is trimmed instead."""
    out = []
    for s, e, join, was in spans:
        for q0, q1 in audio.quiet_runs(src, s + 0.05, e - 0.05, frames=round(gap_max * 100)):
            if q0 - s < 0.1:
                s = max(s, q1 - 0.06)
            elif e - q1 < 0.1:
                e = min(e, q0 + 0.10)
            else:
                out.append((s, q0 + pause_keep / 2, join, was))
                s, join, was = q1 - pause_keep / 2, 'pause', q1 - q0
        out.append((s, e, join, was))
    return out


def subtract(spans, drops):
    """Remove drop ranges from (start, end, join, pause_was) spans; a piece after a drop joins as 'drop'."""
    for d0, d1 in drops:
        out = []
        for s, e, kind, was in spans:
            if d1 <= s or d0 >= e:
                out.append((s, e, kind, was))
                continue
            if d0 > s:
                out.append((s, d0, kind, was))
            if d1 < e:
                out.append((d1, e, 'drop', None))
        spans = out
    return spans


def build_edl(spec, transcripts, fps=30, pad_in=0.06, pad_out=0.10, gap_max=0.75, pause_keep=0.45, refine=True):
    audio = Audio(spec['sources']) if refine else None
    cache, cursor = {}, {}
    segments, dropped, report, total = [], [], [], 0.0
    for section in spec['sections']:
        src = section['source']
        if src not in cache:
            words = load_words(transcripts, src)
            cache[src], cursor[src] = (words, *flatten(words)), 0
        words, text, owner = cache[src]
        kept_text, notes = '', []
        for keep_no, keep in enumerate(section['keeps']):
            a, b, force_start, force_end, drops = parse_keep(keep)
            i = text.find(a, cursor[src])
            if i < 0:
                raise ValueError(f'[{section["id"]}] start anchor not found after char {cursor[src]}: {a}')
            j = text.find(b, i)
            if j < 0:
                raise ValueError(f'[{section["id"]}] end anchor not found: {b}')
            j_end = j + len(b) - 1
            cursor[src] = j_end + 1
            w0, w1 = owner[i], owner[j_end]
            runs, run_start = [], w0
            for k in range(w0, w1):
                if words[k + 1]['start'] - words[k]['end'] > gap_max:
                    runs.append((run_start, k))
                    run_start = k + 1
            runs.append((run_start, w1))
            spans = []
            for n, (r0, r1) in enumerate(runs):
                first, last = n == 0, n == len(runs) - 1
                prev_end = words[r0 - 1]['end'] if r0 > 0 else 0.0
                next_start = words[r1 + 1]['start'] if r1 + 1 < len(words) else words[r1]['end'] + 1
                s = max(prev_end + 0.01, words[r0]['start'] - pad_in)
                e = min(next_start - 0.01, words[r1]['end'] + pad_out)
                if not last:
                    e = min(words[r1]['end'] + pause_keep / 2, next_start - 0.01)
                if not first:
                    s = max(words[r0]['start'] - pause_keep / 2, prev_end + 0.01)
                if audio and first and force_start is None and r0 > 0:
                    s = audio.refine_start(src, s, words[r0])
                if audio and last and force_end is None:
                    e = audio.refine_end(src, words[r1], e)
                if first and force_start is not None:
                    s = force_start
                if last and force_end is not None:
                    e = force_end
                join = 'pause' if not first else ('section' if keep_no == 0 else 'keep')
                spans.append((s, e, join, None if first else words[r0]['start'] - words[r0 - 1]['end']))
            if audio:
                spans = split_silences(audio, src, spans, gap_max, pause_keep)
            snapped = []
            for d0, d1 in sorted(drops):
                if d1 <= d0:
                    raise ValueError(f'[{section["id"]}] drop [{d0}, {d1}] is empty')
                if audio:
                    d0, d1 = audio.snap(src, d0), audio.snap(src, d1)
                if not any(d0 < e and d1 > s for s, e, _, _ in spans):
                    raise ValueError(f'[{section["id"]}] drop [{d0:.2f}, {d1:.2f}] lies outside keep {a}…{b}')
                said = ''.join(w['text'].replace(' ', '') for w in words
                               if w['start'] >= d0 - 0.02 and w['end'] <= d1 + 0.02)
                notes.append(f'  删去 {d0:.2f}–{d1:.2f}s：{said or "没有完整的字（停顿、拖音或未转录的声音）"}')
                dropped.append({'section': section['id'], 'source': src, 'start': round(d0, 4), 'end': round(d1, 4)})
                snapped.append((d0, d1))
            for s, e, join, was in subtract(spans, snapped):
                if snapped and e - s < MIN_PIECE:
                    notes.append(f'  丢弃过短残片 {s:.2f}–{e:.2f}s')
                    continue
                exact = (e - s) * fps
                # A piece that stops at a drop never rounds up into the dropped sound.
                count = max(1, int(exact + 1e-6) if any(abs(e - d0) < 1e-6 for d0, _ in snapped) else round(exact))
                e = s + count / fps
                segments.append({'section': section['id'], 'source': src, 'start': round(s, 4), 'end': round(e, 4),
                                 'join': join})
                if join == 'pause' and was:
                    segments[-1]['pause_was'] = round(was, 2)
                total += e - s
            kept_text += text[i:j_end + 1]
        report.append('\n'.join([f'{section["id"]}: {kept_text}'] + notes))
    edl = {'sources': spec['sources'], 'fps': fps, 'segments': segments, 'total_seconds': round(total, 2)}
    if dropped:
        edl['dropped'] = dropped
    edl['suspects'] = find_suspects(edl, {src: c[0] for src, c in cache.items()}, audio)
    report.append(suspects_text(edl['suspects']))
    return edl, '\n\n'.join(report)


def frames_of(segment, fps):
    return max(1, round((segment['end'] - segment['start']) * fps))


def word_owners(edl, words, min_overlap=0.08):
    """(source, word index) -> segment index. A word belongs to the segment holding its midpoint. When the midpoint
    was cut away (ASR folded a pause or a dropped false start into the word's timing), the word belongs to the
    segment keeping most of it, provided that part is long enough to be the spoken syllable."""
    owners = {}
    for src, ws in words.items():
        segs = [(n, s) for n, s in enumerate(edl['segments']) if s['source'] == src]
        for k, w in enumerate(ws):
            mid = (w['start'] + w['end']) / 2
            hit = next((n for n, s in segs if s['start'] <= mid < s['end']), None)
            if hit is None:
                overlap, n = max(((min(w['end'], s['end']) - max(w['start'], s['start']), n) for n, s in segs),
                                 default=(0, None))
                hit = n if overlap >= min_overlap else None
            if hit is not None:
                owners[src, k] = hit
    return owners


def segment_offsets(edl):
    fps = edl.get('fps', 30)
    out, t = [], 0.0
    for seg in edl['segments']:
        out.append(t)
        t += frames_of(seg, fps) / fps
    return out, t


def kept_chars(edl, words):
    """Kept word characters in cut order: dicts with char, word, section, source and cut/source times."""
    owners = word_owners(edl, words)
    offsets, _ = segment_offsets(edl)
    by_seg = {}
    for (src, k), n in owners.items():
        by_seg.setdefault(n, []).append(k)
    chars = []
    for n, seg in enumerate(edl['segments']):
        for k in sorted(by_seg.get(n, [])):
            w = words[seg['source']][k]
            piece = w['text'].replace(' ', '')
            s, e = max(w['start'], seg['start']), min(w['end'], seg['end'])
            step = (e - s) / max(1, len(piece))
            for m, c in enumerate(piece):
                chars.append({'c': c, 'word': k, 'seg': n, 'section': seg['section'], 'source': seg['source'],
                              'src_t': s + m * step, 'src_e': s + (m + 1) * step,
                              't': offsets[n] + s + m * step - seg['start']})
    return chars


def find_suspects(edl, words, audio=None, long_per_char=0.42, pause_min=0.40):
    """Listening targets inside the kept material. Text heuristics always; untranscribed sound only with audio."""
    chars = kept_chars(edl, words)
    offsets, _ = segment_offsets(edl)
    spoken = [c for c in chars if WORD_CHAR.match(c['c'])]
    text = ''.join(c['c'] for c in spoken)
    found = []

    position = {id(c): n for n, c in enumerate(chars)}

    def add(kind, first, last, note=''):
        i0, i1 = position[id(first)], position[id(last)]
        before = ''.join(c['c'] for c in chars[max(0, i0 - 6):i0])
        after = ''.join(c['c'] for c in chars[i1 + 1:i1 + 7])
        context = before + '[' + ''.join(c['c'] for c in chars[i0:i1 + 1]) + ']' + after
        found.append({'kind': kind, 'section': first['section'], 'source': first['source'],
                      'start': round(first['src_t'], 3), 'end': round(last['src_e'], 3),
                      'cut_t': round(first['t'], 3), 'cut_e': round(last['t'] + last['src_e'] - last['src_t'], 3),
                      'context': context, 'note': note})

    def add_pause(n, src_t, src_e, cut_t, cut_e, note):
        """A pause marked between the characters around it: '一段|原始'."""
        before = ''.join(c['c'] for c in chars if c['t'] < cut_t)[-6:]
        after = ''.join(c['c'] for c in chars if c['t'] >= cut_t)[:6]
        seg = edl['segments'][n]
        found.append({'kind': 'pause', 'section': seg['section'], 'source': seg['source'],
                      'start': round(src_t, 3), 'end': round(src_e, 3), 'cut_t': round(cut_t, 3),
                      'cut_e': round(cut_e, 3), 'context': f'{before}|{after}', 'note': note})

    i = 0
    while i < len(spoken):
        hit = 0
        for n in (4, 3, 2, 1):
            if i + 2 * n <= len(spoken) and text[i:i + n] == text[i + n:i + 2 * n]:
                a, b = spoken[i + n - 1], spoken[i + n]
                if n > 1 or (a['word'] != b['word'] and b['src_t'] - a['src_e'] >= 0.12):
                    hit = n
                    break
        if hit:
            add('repeat', spoken[i], spoken[i + 2 * hit - 1])
            i += 2 * hit
        else:
            i += 1
    for (src, k), group in groupby(chars, key=lambda c: (c['source'], c['word'])):
        group = list(group)
        token = words[src][k]['text'].strip().strip('，。！？、,.!?').lower()
        letters = sum(1 for d in group if WORD_CHAR.match(d['c']))
        dur = group[-1]['src_e'] - group[0]['src_t']
        if audio:      # ASR word spans often include the following pause; count only the voiced part
            dur = sum(e - s for s, e in audio.voiced_islands(src, group[0]['src_t'], group[-1]['src_e']))
        if token in FILLERS:
            add('filler', group[0], group[-1])
        elif letters and not token.isascii() and dur / letters > long_per_char:
            how = '有声' if audio else '转录时长（未分析音量，可能含停顿）'
            add('long', group[0], group[-1], f'{how} {dur:.2f}s / {letters} 字：拖音，或重复起头被并进了这个词')
    for n, seg in enumerate(edl['segments']):
        if seg.get('pause_was'):
            add_pause(n, seg['start'], seg['start'], offsets[n], offsets[n], f'原 {seg["pause_was"]:.2f}s，已压短')
        if audio:
            for q0, q1 in audio.quiet_runs(seg['source'], seg['start'] + 0.03, seg['end'] - 0.03,
                                           frames=round(pause_min * 100)):
                if q0 - seg['start'] < 0.1 or seg['end'] - q1 < 0.1:
                    continue      # the kept half of a pause already listed at the join
                cut = offsets[n] + q0 - seg['start']
                add_pause(n, q0, q1, cut, cut + q1 - q0, f'{q1 - q0:.2f}s')
    if not audio:
        for a, b in zip(chars, chars[1:]):
            if a['seg'] == b['seg'] and a['word'] != b['word']:
                gap = b['src_t'] - a['src_e']
                if gap >= pause_min and not words[a['source']][a['word']]['text'].rstrip().endswith(END_PUNCT):
                    add_pause(a['seg'], a['src_e'], b['src_t'], a['t'] + a['src_e'] - a['src_t'], b['t'],
                              f'{gap:.2f}s')
    if audio:
        for n, seg in enumerate(edl['segments']):
            ws = words[seg['source']]
            for s, e in audio.voiced_islands(seg['source'], seg['start'], seg['end']):
                if e - s < 0.10 or any(w['start'] - 0.08 < e and w['end'] + 0.08 > s for w in ws):
                    continue
                cut = offsets[n] + s - seg['start']
                found.append({'kind': 'noise', 'section': seg['section'], 'source': seg['source'],
                              'start': round(s, 3), 'end': round(e, 3), 'cut_t': round(cut, 3),
                              'cut_e': round(cut + e - s, 3), 'context': '',
                              'note': '可能是失败起头、气声或杂音'})
    return sorted(found, key=lambda f: f['cut_t'])


def suspects_text(suspects):
    pauses = [f for f in suspects if f['kind'] == 'pause']
    others = [f for f in suspects if f['kind'] != 'pause']
    lines = []
    if pauses:
        lines += ['停顿表（"|" 是停顿位置。按语义判断：句间、分句间是正常换气；落在词中或短语中间就是卡壳，'
                  '用 drop 压短或删掉）：']
        lines += [f'  {clock(f["cut_t"])}  {f["section"]}  {f["note"]:<12}  {f["context"]}' for f in pauses]
        lines.append('')
    if not others:
        return '\n'.join(lines + ['其他疑点：工具未标出。仍需试听剪点与整句衔接。'])
    lines.append('其他疑点（按文字与音量标出的试听目标，不是结论；听过是自然表达就保留）：')
    for f in others:
        detail = f'"{f["context"]}"' if f['context'] else ''
        note = f'  {f["note"]}' if f['note'] else ''
        lines.append(f'  {clock(f["cut_t"])}  {f["section"]}  {KIND_LABEL[f["kind"]]}  {detail}'
                     f'  源 {f["source"]} {f["start"]:.2f}–{f["end"]:.2f}s{note}')
    return '\n'.join(lines)


def render(edl, out, work, fps=30, size=None, crf_seg=14, crf_out=18):
    """Extract each segment with exactly N frames and N*(48000/fps) samples, then join with the concat filter."""
    if SR_OUT % fps:
        raise ValueError(f'fps {fps} does not divide {SR_OUT}; choose 24/25/30/48/50/60')
    spf = SR_OUT // fps
    work.mkdir(parents=True, exist_ok=True)
    scale = f',scale={size.replace("x", ":")}' if size else ''
    files, counts = [], []
    for n, seg in enumerate(edl['segments']):
        count = frames_of(seg, fps)
        dur = count / fps
        part = work / f'seg_{n:03d}_{seg["source"]}_{seg["start"]:.4f}_{count}.mkv'
        files.append(part)
        counts.append(count)
        if part.exists():
            continue
        subprocess.run([ffmpeg(), '-loglevel', 'error', '-y', '-ss', f'{seg["start"]:.4f}',
                        '-i', edl['sources'][seg['source']], '-frames:v', str(count),
                        '-vf', f'fps={fps}{scale},setsar=1,format=yuv420p',
                        '-af', f'aresample={SR_OUT},apad,atrim=end_sample={count * spf},'
                               f'afade=t=in:st=0:d=0.03,afade=t=out:st={dur - 0.03:.4f}:d=0.03',
                        '-c:v', 'libx264', '-crf', str(crf_seg), '-preset', 'veryfast',
                        '-c:a', 'pcm_s16le', '-ar', str(SR_OUT), '-ac', '2', str(part)], check=True)
    graph = ';'.join(f'[{i}:v]trim=end_frame={c},setpts=PTS-STARTPTS[v{i}];'
                     f'[{i}:a]asetpts=PTS-STARTPTS,apad,atrim=end_sample={c * spf},asetpts=PTS-STARTPTS[a{i}]'
                     for i, c in enumerate(counts))
    graph += ';' + ''.join(f'[v{i}][a{i}]' for i in range(len(files))) + f'concat=n={len(files)}:v=1:a=1[v][a]'
    graph_file = work / 'concat_graph.txt'
    graph_file.write_text(graph, encoding='utf-8')
    cmd = [ffmpeg(), '-loglevel', 'error', '-y']
    for part in files:
        cmd += ['-i', str(part)]
    # ffmpeg 9 removed -filter_complex_script; '-/filter_complex <file>' reads the graph from a file.
    cmd += ['-/filter_complex', str(graph_file), '-map', '[v]', '-map', '[a]',
            '-c:v', 'libx264', '-crf', str(crf_out), '-preset', 'fast', '-pix_fmt', 'yuv420p', '-r', str(fps),
            '-c:a', 'aac', '-b:a', '192k', '-ar', str(SR_OUT), '-ac', '2', '-movflags', '+faststart', str(out)]
    subprocess.run(cmd, check=True)
    return {'frames': sum(counts), 'seconds': round(sum(counts) / fps, 3), 'segments': len(files)}


def build_cues(edl, transcripts):
    """Every kept character's start/end in the cut voice timeline, plus section spans."""
    fps = edl.get('fps', 30)
    words = {src: load_words(transcripts, src) for src in edl['sources']}
    owners = word_owners(edl, words)
    by_seg = {}
    for (src, k), n in owners.items():
        by_seg.setdefault(n, []).append(k)
    chars, sections, t_out = [], {}, 0.0
    for n, seg in enumerate(edl['segments']):
        dur = frames_of(seg, fps) / fps
        for k in sorted(by_seg.get(n, [])):
            w = words[seg['source']][k]
            for c in w['text'].replace(' ', ''):
                chars.append({'sec': seg['section'], 'c': c,
                              't': round(t_out + max(w['start'], seg['start']) - seg['start'], 3),
                              'e': round(t_out + min(w['end'], seg['end']) - seg['start'], 3)})
        span = sections.setdefault(seg['section'], {'id': seg['section'], 'start': round(t_out, 4)})
        t_out += dur
        span['end'] = round(t_out, 4)
    return chars, list(sections.values())


def parse_clock(value):
    """'52.3', '0:52.3' or '1:02:03' -> seconds."""
    seconds = 0.0
    for part in str(value).strip().split(':'):
        seconds = seconds * 60 + float(part)
    return seconds


LISTEN_KINDS = ('repeat', 'long', 'filler', 'noise')


def listen_windows(edl, pad=2.0, all_cuts=False, at=(), kinds=LISTEN_KINDS):
    """Cut-timeline windows to audition: edits that removed material, suspects of the given kinds, and
    user-named times. Pauses are judged from the report by meaning first, so they join only when asked for;
    pause-shortening joins likewise only with all_cuts. Overlapping windows merge."""
    offsets, total = segment_offsets(edl)
    marks = []
    for n, seg in enumerate(edl['segments'][1:], start=1):
        kind = seg.get('join', 'keep')
        if all_cuts or kind != 'pause':
            marks.append((offsets[n], offsets[n], f'剪点（{JOIN_LABEL.get(kind, kind)}）', seg['section']))
    for f in edl.get('suspects', []):
        if f['kind'] not in kinds:
            continue
        marks.append((f['cut_t'], f['cut_e'], f'{KIND_LABEL[f["kind"]]} {f["context"]}'.strip(), f['section']))
    for t in at:
        marks.append((t, t, KIND_LABEL['at'], ''))
    windows = []
    for t0, t1, label, section in sorted(marks):
        s, e = max(0.0, t0 - pad), min(total, t1 + pad)
        if windows and s <= windows[-1]['end']:
            windows[-1]['end'] = max(windows[-1]['end'], e)
            windows[-1]['reasons'].append(f'{clock(t0)} {label}')
        else:
            windows.append({'start': s, 'end': e, 'reasons': [f'{clock(t0)} {label}'], 'section': section})
    for w in windows:
        w['start'], w['end'] = round(w['start'], 3), round(w['end'], 3)
        w['source'] = cut_to_source(edl, w['start'], w['end'], offsets)
    return windows


def cut_to_source(edl, t0, t1, offsets):
    """Source range under a cut window when both ends fall in the same source, else None."""
    def locate(t):
        for n, seg in enumerate(edl['segments']):
            dur = frames_of(seg, edl.get('fps', 30)) / edl.get('fps', 30)
            if offsets[n] <= t <= offsets[n] + dur:
                return seg['source'], seg['start'] + t - offsets[n]
        return None
    a, b = locate(t0), locate(t1)
    if a and b and a[0] == b[0] and b[1] > a[1]:
        return {'source': a[0], 'start': round(a[1], 3), 'end': round(b[1], 3)}
    return None


def render_listen(edl, video, windows, out_dir, with_source=False, gap=0.6):
    """One small clip per window (black/silent tail as separator), a compilation, and a checklist."""
    out_dir.mkdir(parents=True, exist_ok=True)
    clips, lines, cursor = [], ['# 试听清单', '', f'合集：试听合集.mp4（每段后有 {gap}s 黑场）', '',
                                '| # | 合集内 | 剪后时间 | 听什么 | 原素材 |', '|---|---|---|---|---|'], 0.0
    vf = f'scale=540:-2,fps=30,format=yuv420p,tpad=stop_mode=add:stop_duration={gap}:color=black'
    for n, w in enumerate(windows, start=1):
        dur = w['end'] - w['start']
        clip = out_dir / f'{n:02d}_{clock(w["start"]).replace(":", "m")}s.mp4'
        subprocess.run([ffmpeg(), '-loglevel', 'error', '-y', '-ss', f'{w["start"]:.3f}', '-i', str(video),
                        '-t', f'{dur:.3f}', '-vf', vf, '-af', f'aresample=48000,apad=pad_dur={gap}',
                        '-t', f'{dur + gap:.3f}', '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast',
                        '-c:a', 'aac', '-b:a', '128k', '-ac', '2', str(clip)], check=True)
        clips.append(clip)
        src_note = ''
        if with_source and w['source']:
            src = w['source']
            src_clip = out_dir / f'{n:02d}_原素材.mp4'
            subprocess.run([ffmpeg(), '-loglevel', 'error', '-y', '-ss', f'{src["start"]:.3f}',
                            '-i', edl['sources'][src['source']], '-t', f'{src["end"] - src["start"]:.3f}',
                            '-vf', 'scale=540:-2,fps=30,format=yuv420p', '-c:v', 'libx264', '-crf', '28',
                            '-preset', 'veryfast', '-c:a', 'aac', '-b:a', '128k', '-ac', '2', str(src_clip)], check=True)
            src_note = f'{src_clip.name}（{src["start"]:.2f}–{src["end"]:.2f}s）'
        elif w['source']:
            src_note = f'{w["source"]["source"]} {w["source"]["start"]:.2f}–{w["source"]["end"]:.2f}s'
        lines.append(f'| {n} | {clock(cursor)} | {clock(w["start"])}–{clock(w["end"])} | '
                     f'{"；".join(w["reasons"])} | {src_note} |')
        cursor += dur + gap
    if clips:
        graph = ''.join(f'[{i}:v][{i}:a]' for i in range(len(clips))) + f'concat=n={len(clips)}:v=1:a=1[v][a]'
        cmd = [ffmpeg(), '-loglevel', 'error', '-y']
        for clip in clips:
            cmd += ['-i', str(clip)]
        cmd += ['-filter_complex', graph, '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '28',
                '-preset', 'veryfast', '-c:a', 'aac', '-b:a', '128k', str(out_dir / '试听合集.mp4')]
        subprocess.run(cmd, check=True)
    lines += ['', '听完记下：哪一处不自然、像哪一类（重复起音 / 字尾拖延 / 句内犹豫 / 剪断字音 / 停顿过长或过短）。']
    return '\n'.join(lines) + '\n', len(clips)


def write_out(path, text, force):
    """Exclusive create unless force: earlier edits stay recoverable."""
    with Path(path).open('w' if force else 'x', encoding='utf-8') as stream:
        stream.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--force', action='store_true', help='overwrite existing output files')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('edl')
    p.add_argument('keeps', type=Path)
    p.add_argument('--transcripts', type=Path, help='default: <keeps dir>/transcripts')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--report', type=Path, help='readable kept text and suspected stumbles for checking')
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--pad-in', type=float, default=0.06)
    p.add_argument('--pad-out', type=float, default=0.10)
    p.add_argument('--gap-max', type=float, default=0.75)
    p.add_argument('--pause-keep', type=float, default=0.45)
    p.add_argument('--no-refine', action='store_true', help='skip audio-based cut refinement and noise scan')
    p = sub.add_parser('render')
    p.add_argument('edl', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--work', type=Path, help='segment cache dir; default: <out dir>/voice_segs')
    p.add_argument('--size', help='e.g. 1080x1920; default keeps source size')
    p = sub.add_parser('cues')
    p.add_argument('edl', type=Path)
    p.add_argument('--transcripts', type=Path, required=True)
    p.add_argument('--out-dir', type=Path, required=True)
    p = sub.add_parser('listen')
    p.add_argument('edl', type=Path)
    p.add_argument('--video', type=Path, required=True, help='the rendered cut this EDL produced')
    p.add_argument('--out-dir', type=Path, required=True)
    p.add_argument('--pad', type=float, default=2.0, help='seconds of context on each side')
    p.add_argument('--at', default='', help='extra cut-timeline times, e.g. "0:52,0:55.4"')
    p.add_argument('--all-cuts', action='store_true', help='also audition pause-shortening joins')
    p.add_argument('--kinds', default=','.join(LISTEN_KINDS),
                   help='suspect kinds to audition; add "pause" to include every listed pause')
    p.add_argument('--with-source', action='store_true', help='also cut the unedited source under each window')
    args = parser.parse_args(argv)
    try:
        if args.command == 'edl':
            transcripts = args.transcripts or args.keeps.parent / 'transcripts'
            spec = json.loads(args.keeps.read_text(encoding='utf-8'))
            edl, report = build_edl(spec, transcripts, args.fps, args.pad_in, args.pad_out,
                                    args.gap_max, args.pause_keep, not args.no_refine)
            write_out(args.out, json.dumps(edl, ensure_ascii=False, indent=1), args.force)
            if args.report:
                write_out(args.report, report, args.force)
            result = {'segments': len(edl['segments']), 'total_seconds': edl['total_seconds'],
                      'suspects': len(edl['suspects'])}
        elif args.command == 'render':
            edl = json.loads(args.edl.read_text(encoding='utf-8'))
            if args.out.exists() and not args.force:
                raise FileExistsError(f'{args.out} exists; pass --force or choose a new name')
            result = render(edl, args.out, args.work or args.out.parent / 'voice_segs', edl.get('fps', 30), args.size)
        elif args.command == 'listen':
            edl = json.loads(args.edl.read_text(encoding='utf-8'))
            checklist = args.out_dir / '试听清单.md'
            if checklist.exists() and not args.force:
                raise FileExistsError(f'{checklist} exists; pass --force or choose a new folder')
            at = [parse_clock(t) for t in args.at.split(',') if t.strip()]
            kinds = tuple(k.strip() for k in args.kinds.split(',') if k.strip())
            windows = listen_windows(edl, args.pad, args.all_cuts, at, kinds)
            text, count = render_listen(edl, args.video, windows, args.out_dir, args.with_source)
            write_out(checklist, text, True)
            result = {'clips': count, 'checklist': str(checklist)}
        else:
            edl = json.loads(args.edl.read_text(encoding='utf-8'))
            chars, sections = build_cues(edl, args.transcripts)
            args.out_dir.mkdir(parents=True, exist_ok=True)
            write_out(args.out_dir / 'cue_chars.json', json.dumps(chars, ensure_ascii=False), args.force)
            write_out(args.out_dir / 'sections.json', json.dumps(sections, ensure_ascii=False, indent=1), args.force)
            result = {'chars': len(chars), 'sections': len(sections),
                      'total_seconds': sections[-1]['end'] if sections else 0}
        print(json.dumps({'ok': True, **result}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(json.dumps({'ok': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
