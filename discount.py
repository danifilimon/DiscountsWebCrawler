from functools import total_ordering


def _is_valid_operand(other):
    return (hasattr(other, "percent") and hasattr(other, "price") and
            hasattr(other, "name") and hasattr(other, "url"))


@total_ordering
class Discount:
    def __init__(self, percent, price, name, url):
        self.percent = float(percent)
        self.price = float(price)
        self.name = str(name).strip()
        self.url = str(url)

    def __eq__(self, other):
        if not _is_valid_operand(other):
            return NotImplemented
        return self.percent == other.percent

    def __lt__(self, other):
        if not _is_valid_operand(other):
            return NotImplemented
        return self.percent < other.percent

    def __repr__(self):
        return 'Discounted ' + "%.0f" % round(self.percent, 2) + \
               '% ( ' + str(self.price) + ' LEI ): ' + self.name + ': ' + self.url
