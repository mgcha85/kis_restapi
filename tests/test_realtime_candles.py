import unittest

def get_realtime_candles(stock_code, candle_type='minute'):
    # Dummy implementation: candle_type에 따른 간단한 캔들 데이터 반환
    if candle_type not in ['minute', 'hour', 'day']:
        raise ValueError('Invalid candle type')
    return [{'time': '2025-03-31 10:00', 'open': 100, 'high': 105, 'low': 95, 'close': 102}]

class TestRealtimeCandles(unittest.TestCase):
    def test_minute_candles(self):
        candles = get_realtime_candles('AAPL', candle_type='minute')
        self.assertIsInstance(candles, list)
        self.assertEqual(candles[0]['open'], 100)
    
    def test_hour_candles(self):
        candles = get_realtime_candles('AAPL', candle_type='hour')
        self.assertIsInstance(candles, list)
    
    def test_day_candles(self):
        candles = get_realtime_candles('AAPL', candle_type='day')
        self.assertIsInstance(candles, list)
    
    def test_invalid_candle_type(self):
        with self.assertRaises(ValueError):
            get_realtime_candles('AAPL', candle_type='invalid')

if __name__ == '__main__':
    unittest.main()
