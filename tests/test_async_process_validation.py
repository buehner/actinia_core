# -*- coding: utf-8 -*-
import unittest
from flask.json import dumps as json_dumps

try:
    from .test_resource_base import ActiniaResourceTestCaseBase, URL_PREFIX
except:
    from test_resource_base import ActiniaResourceTestCaseBase, URL_PREFIX

__license__ = "GPLv3"
__author__ = "Sören Gebbert"
__copyright__ = "Copyright 2016, Sören Gebbert"
__maintainer__ = "Sören Gebbert"
__email__ = "soerengebbert@googlemail.com"

# Module example for r.out.ascii with g.region adjustment and temporary file handling
process_chain_legacy = {
    1: {
        "module": "g.region",
        "inputs": {
            "raster": "elevation@PERMANENT",
            "res": 10000
        },
        "flags": "p",
        "verbose": True
    },
    2: {
        "module": "r.out.ascii",
        "inputs": {
            "input": "elevation@PERMANENT"
        },
        "outputs": {
            "output": {
                "name": "$file::out1"
            }
        }
    },
    3: {
        "executable": "/bin/cat",
        "parameters": ["$file::out1"]
    },
    4: {
        "module": "r.out.ascii",
        "inputs": {
            "input": "elevation@PERMANENT"
        },
        "outputs": {
            "output": {
                "name": "$file::out2"
            }
        }
    },
    5: {
        "executable": "/bin/cat",
        "parameters": ["$file::out2"]
    },
    6: {
        "executable": "/bin/cat",
        "stdin": "5::stdout"
    }
}

# Module  example for r.out.ascii with g.region adjustment and temporary file handling
process_chain_new = {
    "version": 1,
    "webhooks": {"finished": "http://0.0.0.0:5005/webhook/finished",
                 "update": "http://0.0.0.0:5005/webhook/update"},
    "list": [
        {
            "id": "1",
            "module": "g.region",
            "inputs": [
                {"param": "raster",
                 "value": "elevation@PERMANENT"},
                {"param": "res",
                 "value": "10000"}
            ],
            "flags": "p",
            "verbose": True
        },
        {
            "id": "2",
            "module": "r.out.ascii",
            "inputs": [{"param": "input",
                        "value": "elevation@PERMANENT"}],
            "outputs": [
                {"export": {"type": "file", "format": "TXT"},
                 "param": "output",
                 "value": "$file::out1"}
            ]
        },
        {
            "id": "3",
            "exe": "/bin/cat",
            "params": ["$file::out1"]
        },
        {
            "id": "4",
            "module": "r.out.ascii",
            "inputs": [{"param": "input",
                        "value": "elevation@PERMANENT"}],
            "outputs": [
                {"export": {"type": "file", "format": "TXT"},
                 "param": "output",
                 "value": "$file::out2"}
            ]
        },
        {
            "id": "5",
            "exe": "/bin/cat",
            "params": ["$file::out2"]
        },
        {
            "id": "6",
            "exe": "/bin/cat",
            "stdin": "5::stdout"
        }
    ]
}

# Import a Sentinel2A scene and compute the NDVI for a specific polygon
process_chain_ndvi = {
    "list": [
        {"id": "importer_1",
         "module": "importer",
         "inputs": [{"import_descr": {"source": "S2B_MSIL1C_20171010T131249_N0205_R081_T26VPR_20171010T131243",
                                      "type": "sentinel2",
                                      "sentinel_band": "B04"},
                     "param": "map",
                     "value": "B04"},
                    {"import_descr": {"source": "S2B_MSIL1C_20171010T131249_N0205_R081_T26VPR_20171010T131243",
                                      "type": "sentinel2",
                                      "sentinel_band": "B08"},
                     "param": "map",
                     "value": "B08"}]},

        {"id": "g_region_1",
         "module": "g.region",
         "inputs": [{"param": "raster",
                     "value": "B04"}],
         "flags": "g"},

        {"id": "rmapcalc_1",
         "module": "r.mapcalc",
         "inputs": [{"param": "expression",
                     "value": "NDVI = float((B08 - B04)/(B08 + B04))"}]},

        {"id": "r_univar_sentinel2",
         "module": "r.univar",
         "inputs": [{"param": "map",
                     "value": "NDVI"}],
         "flags": "g"},

        {"id": "exporter_1",
         "module": "exporter",
         "outputs": [{"export": {"type": "raster", "format": "GTiff"},
                      "param": "map",
                      "value": "NDVI"}]}
    ],
    "webhooks": {"finished": "http://0.0.0.0:5005/webhook/finished",
                 "update": "http://0.0.0.0:5005/webhook/update"},
    "version": "1"
}

# Import a Sentinel2A scene and compute the NDVI for a specific polygon
# https://storage.googleapis.com/graas-geodata/rio.json
# https://gdh-data-sandbox.ams3.digitaloceanspaces.com/rio.json
process_chain_ndvi_landsat = {
    "list": [
        {"id": "importer_1",
         "module": "importer",
         "inputs": [{"import_descr": {"source": "LT52170762005240COA00",
                                      "type": "landsat",
                                      "landsat_atcor": "dos1"},
                     "param": "map",
                     "value": "ignored"},
                    {"import_descr": {"source": "https://storage.googleapis.com/graas-geodata/rio.json",
                                      "type": "vector"},
                     "param": "map",
                     "value": "polygon"}]},

        {"id": "g_list",
         "module": "g.list",
         "inputs": [{"param": "type",
                     "value": "raster"}]},

        {"id": "g_rename_1",
         "module": "g.rename",
         "inputs": [{"param": "raster",
                     "value": "LT52170762005240COA00_dos1.4,RED"}]},

        {"id": "g_rename_2",
         "module": "g.rename",
         "inputs": [{"param": "raster",
                     "value": "LT52170762005240COA00_dos1.5,NIR"}]},

        {"id": "g_region_1",
         "module": "g.region",
         "inputs": [{"param": "raster",
                     "value": "RED"}],
         "flags": "g"},

        {"id": "g_region_2",
         "module": "g.region",
         "inputs": [{"param": "vector",
                     "value": "polygon"}],
         "flags": "g"},

        {"id": "r_mask",
         "module": "r.mask",
         "inputs": [{"param": "vector",
                     "value": "polygon"}]},

        {"id": "rmapcalc_1",
         "module": "r.mapcalc",
         "inputs": [{"param": "expression",
                     "value": "NDVI = float((NIR - RED)/(NIR + RED))"}]},

        {"id": "r_univar_ndvi",
         "module": "r.univar",
         "inputs": [{"param": "map",
                     "value": "NDVI"}],
         "flags": "g"},

        {"id": "exporter_1",
         "module": "exporter",
         "outputs": [{"export": {"type": "raster", "format": "GTiff"},
                      "param": "map",
                      "value": "NDVI"}]}
    ],
    "webhooks": {"finished": "http://0.0.0.0:5005/webhook/finished",
                 "update": "http://0.0.0.0:5005/webhook/update"},
    "version": "1"
}

process_chain_landsat = {
    "list": [
        {"id": "importer_1",
         "module": "importer",
         "inputs": [{"import_descr": {"source": "LT52170762005240COA00",
                                      "type": "landsat",
                                      "landsat_atcor": "dos1"},
                     "param": "map",
                     "value": "ignored"},
                    {"import_descr": {"source": "LE70030041999205KIS00",
                                      "type": "landsat",
                                      "landsat_atcor": "dos1"},
                     "param": "map",
                     "value": "ignored"},
                    {"import_descr": {"source": "LC80050042013137LGN01",
                                      "type": "landsat",
                                      "landsat_atcor": "dos1"},
                     "param": "map",
                     "value": "ignored"},
                    {"import_descr": {"source": "LE72170762002288CUB00",
                                      "type": "landsat",
                                      "landsat_atcor": "dos1"},
                     "param": "map",
                     "value": "ignored"},
                    {"import_descr": {"source": "LT52170762007278COA00",
                                      "type": "landsat",
                                      "landsat_atcor": "dos1"},
                     "param": "map",
                     "value": "ignored"}
                    ]
         }],
    "webhooks": {"finished": "http://0.0.0.0:5005/webhook/finished"},
    "version": "1"
}

class AsyncProcessValidationTestCase(ActiniaResourceTestCaseBase):
    def test_async_processing_legacy(self):
        rv = self.server.post(URL_PREFIX + '/locations/nc_spm_08/process_chain_validation_sync',
                              headers=self.admin_auth_header,
                              data=json_dumps(process_chain_legacy),
                              content_type="application/json")

        resp = self.waitAsyncStatusAssertHTTP(rv, headers=self.admin_auth_header,
                                              http_status=200, status="finished")
        self.assertEqual(len(resp["process_results"]), 6)

    def test_async_processing_new(self):
        rv = self.server.post(URL_PREFIX + '/locations/nc_spm_08/process_chain_validation_sync',
                              headers=self.admin_auth_header,
                              data=json_dumps(process_chain_new),
                              content_type="application/json")

        resp = self.waitAsyncStatusAssertHTTP(rv, headers=self.admin_auth_header,
                                              http_status=200, status="finished")
        self.assertEqual(len(resp["process_results"]), 6)

    def test_async_processing_new_ndvi(self):
        rv = self.server.post(URL_PREFIX + '/locations/LL/process_chain_validation_async',
                              headers=self.admin_auth_header,
                              data=json_dumps(process_chain_ndvi),
                              content_type="application/json")

        resp = self.waitAsyncStatusAssertHTTP(rv, headers=self.admin_auth_header,
                                              http_status=200, status="finished")
        print(resp)
        self.assertEqual(len(resp["process_results"]), 29)

    def test_async_processing_new_ndvi_export_landsat(self):
        rv = self.server.post(URL_PREFIX + '/locations/LL/process_chain_validation_async',
                              headers=self.admin_auth_header,
                              data=json_dumps(process_chain_ndvi_landsat),
                              content_type="application/json")

        resp = self.waitAsyncStatusAssertHTTP(rv, headers=self.admin_auth_header,
                                              http_status=200, status="finished")
        self.assertEqual(len(resp["process_results"]), 26)

    def test_async_processing_landsat(self):
        rv = self.server.post(URL_PREFIX + '/locations/LL/process_chain_validation_async',
                              headers=self.admin_auth_header,
                              data=json_dumps(process_chain_landsat),
                              content_type="application/json")

        resp = self.waitAsyncStatusAssertHTTP(rv, headers=self.admin_auth_header,
                                              http_status=200, status="finished")
        self.assertEqual(len(resp["process_results"]), 96)


if __name__ == '__main__':
    unittest.main()
