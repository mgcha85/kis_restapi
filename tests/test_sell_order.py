import unittest

def place_sell_order(order_type='limit', qty=1, price=100):
    # Dummy implementation: 지정가('limit')와 시장가('market')만 허용
    if order_type not in ['limit', 'market']:
        raise ValueError('Invalid order type')
    return {'order_type': order_type, 'qty': qty, 'price': price}

class TestSellOrder(unittest.TestCase):
    def test_limit_order(self):
        result = place_sell_order(order_type='limit', qty=8, price=200)
        self.assertEqual(result['order_type'], 'limit')
        self.assertEqual(result['qty'], 8)
        self.assertEqual(result['price'], 200)
        
    def test_market_order(self):
        result = place_sell_order(order_type='market', qty=3, price=0)
        self.assertEqual(result['order_type'], 'market')
        self.assertEqual(result['qty'], 3)
        
    def test_invalid_order_type(self):
        with self.assertRaises(ValueError):
            place_sell_order(order_type='invalid', qty=1, price=100)

if __name__ == '__main__':
    unittest.main()
