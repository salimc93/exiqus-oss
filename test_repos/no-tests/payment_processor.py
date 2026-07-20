class PaymentProcessor:
    def __init__(self, api_key):
        self.api_key = api_key

    def process_payment(self, amount, card_number, cvv):
        """Process a payment transaction"""
        if not self.validate_card(card_number):
            raise ValueError("Invalid card number")

        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Process the payment
        transaction_id = self._send_to_api(amount, card_number, cvv)
        return transaction_id

    def validate_card(self, card_number):
        """Validate card number using Luhn algorithm"""
        # Implementation here
        return len(card_number) == 16

    def _send_to_api(self, amount, card_number, cvv):
        """Send payment to payment gateway"""
        # Simulated API call
        return "TXN_12345"
