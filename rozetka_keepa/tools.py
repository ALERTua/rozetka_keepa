def float_from_str(str_):
    try:
        return float(str_)
    except:  # noqa: E722
        return None


def sell_status_str(sell_status):
    if sell_status == "unavailable":
        return "❌"

    if sell_status == "available":
        return "✅"

    return sell_status
