from vnpy.trader.constant import Offset, Direction
from vnpy.trader.object import TradeData
from vnpy.trader.engine import BaseEngine
from vnpy.app.algo_trading import AlgoTemplate
from datetime import datetime


class MoneywapAlgo(AlgoTemplate):
    """"""

    display_name = "Money 時間平均"

    default_setting = {
        "vt_symbol": "",
        "direction": [Direction.LONG.value, Direction.SHORT.value],
        "total_amt": 0,
        "time_line": "09:00",
        "price": 0.0,
        "offset": [
            Offset.NONE.value,
            Offset.CLOSETODAY.value,
        ]
    }

    variables = [
        "traded", "order_volume", "timer_count", "total_count", "total_amt",
        "interval", "volume", "display_volume"
    ]

    def __init__(self, algo_engine: BaseEngine, algo_name: str, setting: dict):
        """"""
        super().__init__(algo_engine, algo_name, setting)

        # Parameters
        self.vt_symbol = setting["vt_symbol"]
        self.direction = Direction(setting["direction"])
        self.total_amt = setting["total_amt"]
        self.price = setting["price"]
        self.time_line = setting["time_line"]

        self.offset = Offset(setting["offset"])
        self.display_volume = 0
        self.purchased_amount = 0

        end = f'{str(datetime.now().date())} {self.time_line}'
        self.end_datetime = datetime.strptime(end, '%Y-%m-%d %H:%M')

        # Variables
        tick = self.get_tick(self.vt_symbol)
        if tick and self.direction == Direction.LONG:
            self.price = tick.limit_up
        if tick and self.direction == Direction.SHORT:
            self.price = tick.limit_down

        self.volume = self.total_amt // 1000 // tick.limit_down  # 總數量
        self.time = (self.end_datetime - datetime.now()).seconds
        self.interval = self.time // self.volume
        self.order_volume = 1
        self.timer_count = 0
        self.total_count = 0
        self.traded = 0
        print(
            f'{self.vt_symbol} {self.direction},{self.total_amt},{tick.pre_close} 每{self.interval}秒，共{self.volume}'
        )
        self.subscribe(self.vt_symbol)
        self.put_parameters_event()
        self.put_variables_event()

    def on_trade(self, trade: TradeData):
        """"""
        self.traded += trade.volume

        if self.traded >= self.volume:
            self.write_log(f"已交易数量：{self.traded}，总数量：{self.volume}")
            self.stop()
        else:
            self.put_variables_event()

    def on_timer(self):
        """"""
        self.timer_count += 1
        self.total_count += 1
        self.put_variables_event()

        # if self.total_count >= self.time:
        if self.purchased_amount >= self.total_amt:
            self.write_log(
                f"金額交易已滿，合計買進{self.display_volume}張，金額{self.purchased_amount}元"
            )
            self.stop()
            return

        if self.timer_count < self.interval:
            return

        self.timer_count = 0
        tick = self.get_tick(self.vt_symbol)

        if not tick:
            self.write_log(f'無{self.vt_symbol} Tick資料')
            return

        # self.cancel_all()

        left_volume = self.volume - self.traded
        order_volume = min(self.order_volume, left_volume)

        if self.direction == Direction.LONG:
            if tick.ask_price_1 <= self.price:
                self.buy(self.vt_symbol,
                         self.price,
                         order_volume,
                         offset=self.offset)
                self.display_volume += 1
                self.purchased_amount += tick.last_price * 1000
            else:
                self.price = tick.ask_price_5
        else:
            if tick.bid_price_1 >= self.price:
                self.sell(self.vt_symbol,
                          self.price,
                          order_volume,
                          offset=self.offset)
                self.display_volume += 1
                self.purchased_amount += tick.last_price * 1000
            else:
                self.price = tick.bid_price_5
