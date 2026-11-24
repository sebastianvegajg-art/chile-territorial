from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import verificar_bde as bde


FIRST = date(2013, 1, 1)
LAST = date(2014, 12, 31)


def catalog():
    return {"SeriesInfos": [
        {"seriesId": code, "frequencyCode": "ANNUAL", "spanishTitle": "Título sintético"}
        for code in bde.REFERENCE
    ]}


def series(code, value="0", status="OK"):
    return {"Series": {"seriesId": code, "Obs": [
        {"indexDateString": "01-01-2013", "value": value, "statusCode": status}
    ]}}


class VerificationTests(TestCase):
    def test_catalog_requires_all_exact_codes(self):
        payload = catalog()
        payload["SeriesInfos"].pop()
        with self.assertRaisesRegex(bde.VerificationError, "ausentes"):
            bde.annual_catalog(payload)

    def test_zero_and_missing_year(self):
        code = bde.REFERENCE[0]
        result = bde.summarize_series(series(code), code, FIRST, LAST)
        self.assertEqual(result["valores_numericos"], 1)
        self.assertEqual(result["anios_sin_fila"], [2014])

    def test_unknown_series_is_rejected(self):
        with self.assertRaisesRegex(bde.VerificationError, "identidad"):
            bde.summarize_series(series("otra"), bde.REFERENCE[0], FIRST, LAST)

    def test_nan_with_ok_status_is_rejected(self):
        code = bde.REFERENCE[0]
        with self.assertRaisesRegex(bde.VerificationError, "finito"):
            bde.summarize_series(series(code, "NaN"), code, FIRST, LAST)

    def test_manifest_holds_five_verified_artifacts(self):
        def download(token, function, **params):
            payload = catalog() if function == "SearchSeries" else series(params["timeseries"])
            return json.dumps(payload).encode(), payload

        with TemporaryDirectory() as directory, patch.object(bde, "download", download):
            output = Path(directory) / "e01"
            bde.run("ficticio", output, FIRST, LAST)
            manifest = json.loads((output / "manifiesto.json").read_text())
            self.assertEqual(len(manifest["referencias"]), 4)
            self.assertEqual(len(manifest["artefactos"]), 5)
            for artifact in manifest["artefactos"]:
                self.assertEqual(
                    artifact["sha256"], sha256((output / artifact["archivo"]).read_bytes()).hexdigest()
                )
            self.assertNotIn("ficticio", json.dumps(manifest))

    @patch.object(bde, "build_opener")
    def test_echoed_secret_fails(self, build_opener):
        opener = build_opener.return_value
        opener.open.return_value = BytesIO(b'{"Codigo":0,"echo":"clave%2Bficticia"}')
        with self.assertRaisesRegex(bde.VerificationError, "reflejada") as caught:
            bde.download("clave+ficticia", "GetSeries")
        self.assertNotIn("ficticia", str(caught.exception))

    @patch.object(bde, "sleep")
    @patch.object(bde, "build_opener")
    def test_http_error_does_not_disclose_url(self, build_opener, sleep):
        opener = Mock()
        opener.open.side_effect = HTTPError(
            "https://example.test/?token=clave-ficticia", 401, "rechazada", None, None
        )
        build_opener.return_value = opener
        with self.assertRaisesRegex(bde.VerificationError, "HTTP 401") as caught:
            bde.download("clave-ficticia", "GetSeries")
        self.assertNotIn("ficticia", str(caught.exception))
        sleep.assert_not_called()
