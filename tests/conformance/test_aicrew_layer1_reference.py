"""Tests de core/anon_layer1.py (F1, E2): batería de patrones españoles.

Copia de AICrew ``tests/test_anon_layer1.py`` (ver ``reference/aicrew/README.md``).
Único cambio respecto al original: la línea de import, que apunta a la copia
de referencia. Esta suite prueba que la referencia está intacta; la suite de
conformidad del Servicio (criterio 0, P1) reutiliza estos mismos casos.
"""

import unittest

from reference.aicrew import anon_layer1 as layer1


class EmailTests(unittest.TestCase):
    def test_simple_email_removed(self):
        result = layer1.anonymize_layer1("Contacto: juan.perez@empresa.com")
        self.assertNotIn("juan.perez@empresa.com", result.anonymized_text)
        self.assertIn("[EMAIL_1]", result.anonymized_text)
        self.assertEqual(
            [(r.category, r.type) for r in result.removals],
            [(layer1.CATEGORY_DATO_CONTACTO, layer1.TYPE_EMAIL)],
        )

    def test_email_split_across_line_break(self):
        text = "Email: juan.perez@\nempresa.com"
        result = layer1.anonymize_layer1(text)
        self.assertNotIn("juan.perez", result.anonymized_text)
        self.assertNotIn("empresa.com", result.anonymized_text)
        self.assertEqual(result.total_removals, 1)

    def test_email_split_around_at_and_dot(self):
        text = "juan.perez @ empresa . com"
        result = layer1.anonymize_layer1(text)
        self.assertEqual(result.anonymized_text.strip(), "[EMAIL_1]")

    def test_multiple_emails_numbered(self):
        text = "a@x.com y b@y.com"
        result = layer1.anonymize_layer1(text)
        self.assertIn("[EMAIL_1]", result.anonymized_text)
        self.assertIn("[EMAIL_2]", result.anonymized_text)


class PhoneTests(unittest.TestCase):
    def test_phone_with_country_code(self):
        result = layer1.anonymize_layer1("Tel: +34 612 345 678")
        self.assertNotIn("612", result.anonymized_text)
        self.assertEqual(result.total_removals, 1)

    def test_phone_without_separators(self):
        result = layer1.anonymize_layer1("Tel: 912345678")
        self.assertIn("[TELEFONO_1]", result.anonymized_text)

    def test_phone_grouped_2_3_2_2(self):
        result = layer1.anonymize_layer1("Tel: 91 234 56 78")
        self.assertIn("[TELEFONO_1]", result.anonymized_text)
        self.assertNotIn("234", result.anonymized_text)

    def test_phone_with_hyphens(self):
        result = layer1.anonymize_layer1("Tel: 601-234-567")
        self.assertIn("[TELEFONO_1]", result.anonymized_text)

    def test_landline_starting_with_9(self):
        result = layer1.anonymize_layer1("Fijo: 918765432")
        self.assertEqual(result.total_removals, 1)

    def test_non_spanish_number_not_removed(self):
        # No empieza por 6/7/8/9: no es un móvil o fijo español válido.
        result = layer1.anonymize_layer1("Referencia: 512345678")
        self.assertEqual(result.total_removals, 0)


class DniNieTests(unittest.TestCase):
    def test_dni_without_hyphen(self):
        result = layer1.anonymize_layer1("DNI: 12345678Z")
        self.assertNotIn("12345678", result.anonymized_text)
        self.assertEqual(result.removals[0].category, layer1.CATEGORY_IDENTIFICADOR_OFICIAL)

    def test_dni_with_hyphen(self):
        result = layer1.anonymize_layer1("DNI: 12345678-Z")
        self.assertNotIn("12345678", result.anonymized_text)

    def test_dni_with_space(self):
        result = layer1.anonymize_layer1("DNI: 12345678 Z")
        self.assertNotIn("12345678", result.anonymized_text)

    def test_nie(self):
        result = layer1.anonymize_layer1("NIE: X1234567L")
        self.assertNotIn("1234567", result.anonymized_text)

    def test_nie_lowercase_letter_prefix(self):
        result = layer1.anonymize_layer1("NIE: x1234567l")
        self.assertNotIn("1234567", result.anonymized_text)


class IbanTests(unittest.TestCase):
    def test_iban_with_spaces(self):
        result = layer1.anonymize_layer1("IBAN: ES91 2100 0418 4502 0005 1332")
        self.assertNotIn("2100", result.anonymized_text)
        self.assertEqual(result.removals[0].category, layer1.CATEGORY_DATO_FINANCIERO)

    def test_iban_without_spaces(self):
        result = layer1.anonymize_layer1("IBAN: ES9121000418450200051332")
        self.assertIn("[IBAN_1]", result.anonymized_text)


class UrlTests(unittest.TestCase):
    def test_https_url(self):
        result = layer1.anonymize_layer1("Perfil: https://www.linkedin.com/in/juanperez")
        self.assertNotIn("linkedin", result.anonymized_text)

    def test_www_without_scheme(self):
        result = layer1.anonymize_layer1("Web: www.ejemplo.com")
        self.assertNotIn("ejemplo.com", result.anonymized_text)


class PostalCodeTests(unittest.TestCase):
    def test_labelled_postal_code(self):
        result = layer1.anonymize_layer1("CP: 28001")
        self.assertIn("[CODIGO_POSTAL_1]", result.anonymized_text)

    def test_labelled_postal_code_full_words(self):
        result = layer1.anonymize_layer1("código postal: 08015")
        self.assertIn("[CODIGO_POSTAL_1]", result.anonymized_text)

    def test_bare_postal_code_in_valid_range(self):
        result = layer1.anonymize_layer1("28001 Madrid")
        self.assertIn("[CODIGO_POSTAL_1]", result.anonymized_text)

    def test_bare_five_digit_number_out_of_range_not_removed(self):
        # Fuera del rango de provincias españolas (01000-52999).
        result = layer1.anonymize_layer1("Cantidad: 99999 unidades")
        self.assertEqual(result.total_removals, 0)

    def test_six_digit_number_not_treated_as_postal_code(self):
        result = layer1.anonymize_layer1("Referencia: 987654")
        self.assertEqual(result.total_removals, 0)


class DateTests(unittest.TestCase):
    def test_full_numeric_date_dmy_removed(self):
        result = layer1.anonymize_layer1("Nacido el 10/07/1990")
        self.assertIn("[FECHA_ABSOLUTA_1]", result.anonymized_text)

    def test_full_numeric_date_with_hyphens(self):
        result = layer1.anonymize_layer1("Fecha: 10-07-1990")
        self.assertIn("[FECHA_ABSOLUTA_1]", result.anonymized_text)

    def test_iso_date_ymd_removed(self):
        result = layer1.anonymize_layer1("Fecha: 1990-07-10")
        self.assertIn("[FECHA_ABSOLUTA_1]", result.anonymized_text)

    def test_textual_spanish_date_removed(self):
        result = layer1.anonymize_layer1("Nacido el 10 de julio de 1990")
        self.assertIn("[FECHA_ABSOLUTA_1]", result.anonymized_text)
        self.assertNotIn("1990", result.anonymized_text)

    def test_month_year_job_period_not_removed(self):
        # Rango de experiencia laboral (mes/año): necesario para E4 (seniority).
        text = "Quality Manager, 03/2020 - 07/2024"
        result = layer1.anonymize_layer1(text)
        self.assertEqual(result.total_removals, 0)
        self.assertIn("03/2020", result.anonymized_text)
        self.assertIn("07/2024", result.anonymized_text)

    def test_bare_year_not_removed(self):
        result = layer1.anonymize_layer1("Graduado en 2015")
        self.assertEqual(result.total_removals, 0)


class LogAndCombinedTests(unittest.TestCase):
    def test_counts_by_category(self):
        text = "juan@x.com, DNI 12345678Z, tel +34 612345678"
        result = layer1.anonymize_layer1(text)
        counts = result.counts_by_category
        self.assertEqual(counts[layer1.CATEGORY_DATO_CONTACTO], 2)  # email + telefono
        self.assertEqual(counts[layer1.CATEGORY_IDENTIFICADOR_OFICIAL], 1)

    def test_log_never_contains_raw_value(self):
        text = "Email personal: juan.perez@empresa.com"
        result = layer1.anonymize_layer1(text)
        for removal in result.removals:
            self.assertNotIn("juan.perez", removal.placeholder)
            self.assertNotIn("empresa.com", removal.placeholder)

    def test_text_without_pii_is_unchanged(self):
        text = "Responsable de calidad con experiencia en auditorías ISO 9001."
        result = layer1.anonymize_layer1(text)
        self.assertEqual(result.anonymized_text, text)
        self.assertEqual(result.total_removals, 0)

    def test_realistic_cv_header(self):
        text = (
            "Juan Pérez García\n"
            "juan.perez@example.com | +34 612 345 678 | DNI 12345678Z\n"
            "C/ Mayor 10, 28001 Madrid\n"
            "LinkedIn: https://www.linkedin.com/in/juanperez\n"
            "Quality Manager, 03/2020 - 07/2024\n"
        )
        result = layer1.anonymize_layer1(text)
        self.assertNotIn("juan.perez@example.com", result.anonymized_text)
        self.assertNotIn("612 345 678", result.anonymized_text)
        self.assertNotIn("12345678", result.anonymized_text)
        self.assertNotIn("linkedin.com/in/juanperez", result.anonymized_text)
        self.assertIn("03/2020 - 07/2024", result.anonymized_text)
        # Los nombres propios sobreviven a la capa 1 por diseño (los quita la capa 2).
        self.assertIn("Juan Pérez García", result.anonymized_text)


if __name__ == "__main__":
    unittest.main()
