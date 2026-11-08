from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Metric:
    column: str
    convert: Callable[[object], float]  # surova ZCL hodnota -> hodnota do DB
    invalid: tuple = ()  # surove hodnoty "nezmereno"
    attr_id: int = 0x0000  # MeasuredValue / Occupancy


METRICS: dict[int, Metric] = {
    0x0402: Metric("temperature", lambda v: v / 100, (-32768,)),  # int16, 0.01 °C
    0x0405: Metric("humidity", lambda v: v / 100, (0xFFFF,)),  # uint16, 0.01 %
    0x040D: Metric("co2", lambda v: round(v * 1_000_000)),  # float, 0.0004 = 400 ppm
    0x0406: Metric("motion", lambda v: int(v) & 1),  # bitmap, 1 = pohyb
}