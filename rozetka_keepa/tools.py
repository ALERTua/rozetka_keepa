def float_from_str(str_):
    try:
        return float(str_)
    except:
        return


def sell_status_str(sell_status):
    if sell_status == 'unavailable':
        return f'❌'
    elif sell_status == 'available':
        return f'✅'
    else:
        return sell_status
