"""The GS1 modulo-10 check digit, shared by every GS1 key that carries one.

Lives here rather than in a general utils module so the ``gs1`` package has no imports
outside the standard library and pydantic, which is what lets it be published on its own.
"""


def calculate_check_digit(number: int | str) -> int:
    """Calculate the GS1 check digit for a number given *without* its check digit.

    The same calculation for every GS1 key that carries a check digit, among them
    GTIN-8/12/13/14, GLN and PGLN (13), GSIN (17), and SSCC and GSRN (18).

    Example:
        >>> calculate_check_digit("629104150021")
        3
    """
    str_number = str(number)
    if not str_number.isdigit():
        raise ValueError("Input must contain only digits")

    total = 0
    for i, digit in enumerate(reversed(str_number)):
        # Weights alternate 3 and 1 from the right, so the position of the check digit
        # itself decides which weight each digit takes.
        multiplier = 3 if i % 2 == 0 else 1
        total += int(digit) * multiplier

    return (10 - (total % 10)) % 10
