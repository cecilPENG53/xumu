import unittest

import mg_inspiration as m


class TestMgInspiration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = m.load()

    def test_index_shape(self):
        tags = set(self.data["use_tags"])
        for e in self.data["entries"]:
            self.assertIn(e["energy"], m.ENERGY)
            self.assertTrue(set(e["vv_uses"]) <= tags, e["slug"])
            for k in ("summary_zh", "borrow_zh", "preview_url", "raw_prompt_url"):
                self.assertTrue(e[k], (e["slug"], k))

    def test_filter_by_use_and_energy(self):
        res = m.select(self.data, ["concept"], "中等", limit=10)
        self.assertTrue(res)
        for e in res:
            self.assertIn("concept", e["vv_uses"])
            self.assertNotEqual(e["energy"], "强")

    def test_limit_and_ranking(self):
        res = m.select(self.data, ["concept", "data"], limit=2)
        self.assertEqual(len(res), 2)
        self.assertEqual(len({"concept", "data"} & set(res[0]["vv_uses"])), 2)

    def test_slug_lookup(self):
        res = m.select(self.data, slugs=["gdgtify-929495"])
        self.assertEqual([e["slug"] for e in res], ["gdgtify-929495"])

    def test_unknown_use_rejected(self):
        self.assertEqual(m.main(["--use", "nope"]), 2)


if __name__ == "__main__":
    unittest.main()
