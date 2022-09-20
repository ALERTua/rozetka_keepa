import asyncio
from copy import copy
from typing import Iterable, List

from aiohttp_retry import ExponentialRetry, RetryClient
from global_logger import Log
from influxdb_client.client.flux_table import FluxTable, FluxRecord
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
# noinspection PyPackageRequirements
from worker import async_worker

from rozetka_keepa import constants

LOG = Log.get_logger()

INFLUXDB_URL = constants.INFLUXDB_URL
INFLUXDB_TOKEN = constants.INFLUXDB_TOKEN
INFLUXDB_ORG = constants.INFLUXDB_ORG
INFLUXDB_BUCKET = constants.INFLUXDB_BUCKET

INFLUX_KWARGS = dict(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG, timeout=600_000_000, enable_gzip=True)
INFLUX_KWARGS_ASYNC = copy(INFLUX_KWARGS)
INFLUX_KWARGS_ASYNC.update(dict(client_session_type=RetryClient,
                                client_session_kwargs={"retry_options": ExponentialRetry(attempts=3)}))


class InfluxDBController:
    cache = []

    def __init__(self, direct=True):
        assert not direct, "please use instantiate classmethod"

    @classmethod
    def instantiate(cls):
        if cls.cache:
            return cls.cache[0]

        output = cls(direct=False)
        cls.cache.append(output)
        return output

    @staticmethod
    @async_worker
    async def _get_points_async_worker(item_ids):
        return InfluxDBController._get_points_async(item_ids=item_ids)

    @staticmethod
    async def _get_points_async(item_ids):
        async with InfluxDBClientAsync(**INFLUX_KWARGS_ASYNC) as client:
            ready = await client.ping()
            if not ready:
                LOG.error(f"InfluxDB NOT READY")
                return

            query_api = client.query_api()

            fltr = f'r["_measurement"] == "{item_ids[0]}"'
            for item_id in item_ids[1:]:
                fltr += f' or r["_measurement"] == "{item_id}"'
            records = await query_api.query(
                f"""import "influxdata/influxdb/schema"
                from(bucket: "{INFLUXDB_BUCKET}")
                    |> range(start: -3y)
                    |> filter(fn: (r) => {fltr})
                    |> filter(fn: (r) => r["_field"] == "price")
                    |> last()
                    |> schema.fieldsAsCols()
                """)

            return records

    @staticmethod
    def _parse_points(points):
        output = {}
        for point in points:
            record: FluxRecord = point.records[0]
            item_id = int(record.values['_measurement'])
            price = float(record.values['price'])
            output[item_id] = price
        return output

    @staticmethod
    def get_prices(item_ids):
        if not isinstance(item_ids, Iterable):
            item_ids = [item_ids]
        crtn = asyncio.run(InfluxDBController._get_points_async_worker(item_ids))
        crtn.wait()
        points: List[FluxTable] = crtn.ret
        return InfluxDBController._parse_points(points)

    @staticmethod
    async def get_prices_async(item_ids):
        if not isinstance(item_ids, Iterable):
            item_ids = [item_ids]

        points = await InfluxDBController._get_points_async(item_ids)
        return InfluxDBController._parse_points(points)


if __name__ == '__main__':
    output_ = InfluxDBController.get_prices([100001384, 100001630])
    pass
