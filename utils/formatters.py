def format_int_to_price(price: int) -> str:
    """Return a str representing CLP"""
    return f'{price:,}$'.replace(',', '.')
