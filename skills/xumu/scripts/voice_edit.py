#!/usr/bin/env python3
"""Talking-head voice editing: anchor keeps -> word-boundary EDL -> frame-exact cut -> per-character cue map.

  edl     keeps.json + transcripts/<source>.json  ->  edl_voice.json (+ readable check text)
  render  edl_voice.json                          ->  one frame-exact A/V file (concat *filter*, single encode)
  cues    edl_voice.json + transcripts            ->  cue_chars.json + sections.json (cut-timeline seconds)

Transcripts use the ElevenLabs Scribe layout that Video Use writes: {"words": [{"text", "start", "end", "type"}]}.

keeps.json:
  {"sources": {"<name>": "<media path>"},
   "sections": [{"id": "B01", "source": "<name>",
                 "keeps": [[start_anchor, end_anchor, force_start_s?, force_end_s?], ...]}]}
Anchors are substrings of the source transcript with spaces removed. Each keep is searched after the previous keep
of the same source, so repeated phrases resolve in reading order. force_* (seconds or null) override a cut point
when ASR timing merged a restart ("OPC，OPC") into one word.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

SR_ANALYSIS = 16000   # analysis rate for cut refinement; 10 ms RMS frames
SR_OUT = 48000


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


def build_edl(spec, transcripts, fps=30, pad_in=0.06, pad_out=0.10, gap_max=0.75, pause_keep=0.45, refine=True):
    audio = Audio(spec['sources']) if refine else None
    cache, cursor = {}, {}
    segments, report, total = [], [], 0.0
    for section in spec['sections']:
        src = section['source']
        if src not in cache:
            words = load_words(transcripts, src)
            cache[src], cursor[src] = (words, *flatten(words)), 0
        words, text, owner = cache[src]
        kept_text = ''
        for keep in section['keeps']:
            a, b = keep[0], keep[1]
            force_start = keep[2] if len(keep) > 2 else None
            force_end = keep[3] if len(keep) > 3 else None
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
                e = s + max(1, round((e - s) * fps)) / fps      # whole-frame length
                segments.append({'section': section['id'], 'source': src, 'start': round(s, 4), 'end': round(e, 4)})
                total += e - s
            kept_text += text[i:j_end + 1]
        report.append(f'{section["id"]}: {kept_text}')
    edl = {'sources': spec['sources'], 'fps': fps, 'segments': segments, 'total_seconds': round(total, 2)}
    return edl, '\n\n'.join(report)


def frames_of(segment, fps):
    return max(1, round((segment['end'] - segment['start']) * fps))


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
    chars, sections, t_out = [], {}, 0.0
    for seg in edl['segments']:
        dur = frames_of(seg, fps) / fps
        for w in words[seg['source']]:
            mid = (w['start'] + w['end']) / 2
            if seg['start'] <= mid < seg['end']:
                for c in w['text'].replace(' ', ''):
                    chars.append({'sec': seg['section'], 'c': c,
                                  't': round(t_out + w['start'] - seg['start'], 3),
                                  'e': round(t_out + min(w['end'], seg['end']) - seg['start'], 3)})
        span = sections.setdefault(seg['section'], {'id': seg['section'], 'start': round(t_out, 4)})
        t_out += dur
        span['end'] = round(t_out, 4)
    return chars, list(sections.values())


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
    p.add_argument('--report', type=Path, help='readable kept text for checking')
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--pad-in', type=float, default=0.06)
    p.add_argument('--pad-out', type=float, default=0.10)
    p.add_argument('--gap-max', type=float, default=0.75)
    p.add_argument('--pause-keep', type=float, default=0.45)
    p.add_argument('--no-refine', action='store_true', help='skip audio-based cut refinement')
    p = sub.add_parser('render')
    p.add_argument('edl', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--work', type=Path, help='segment cache dir; default: <out dir>/voice_segs')
    p.add_argument('--size', help='e.g. 1080x1920; default keeps source size')
    p = sub.add_parser('cues')
    p.add_argument('edl', type=Path)
    p.add_argument('--transcripts', type=Path, required=True)
    p.add_argument('--out-dir', type=Path, required=True)
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
            result = {'segments': len(edl['segments']), 'total_seconds': edl['total_seconds']}
        elif args.command == 'render':
            edl = json.loads(args.edl.read_text(encoding='utf-8'))
            if args.out.exists() and not args.force:
                raise FileExistsError(f'{args.out} exists; pass --force or choose a new name')
            result = render(edl, args.out, args.work or args.out.parent / 'voice_segs', edl.get('fps', 30), args.size)
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
