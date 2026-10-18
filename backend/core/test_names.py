from django.test import SimpleTestCase

from .names import compute_sort_key


class ComputeSortKeyTests(SimpleTestCase):
    def test_surname_first_then_given_name(self):
        self.assertEqual(compute_sort_key("Jana Novotná"), "novotna jana")
        self.assertEqual(compute_sort_key("Novák, Jan"), "novak jan")

    def test_multi_word_surname_uses_family_base(self):
        self.assertEqual(compute_sort_key("Robert van der Sar"), "sar robert")
        self.assertEqual(compute_sort_key("Juan de la Vega"), "vega juan")

    def test_middle_names_stay_with_given_names(self):
        self.assertEqual(compute_sort_key("Mary Ann Smith"), "smith mary ann")

    def test_titles_and_suffixes_do_not_enter_the_key(self):
        self.assertEqual(
            compute_sort_key("Ing. Jan Novák, CSc."),
            "novak jan",
        )

    def test_mononym_sorts_by_its_only_name(self):
        self.assertEqual(compute_sort_key("Cher"), "cher")

    def test_blank_name_has_empty_key(self):
        self.assertEqual(compute_sort_key(""), "")
        self.assertEqual(compute_sort_key("   "), "")

    def test_czech_diacritics_sort_between_ascii_letters(self):
        names = ["Zdeněk Zeman", "Lucie Šimková", "Klára Sýkorová", "Jana Novotná"]
        ordered = sorted(names, key=compute_sort_key)
        self.assertEqual(
            ordered,
            ["Jana Novotná", "Lucie Šimková", "Klára Sýkorová", "Zdeněk Zeman"],
        )
