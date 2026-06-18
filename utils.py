# used to parse fractions as floats
def parse_num(num_str : str):
    try:
        slash_split = num_str.split('/')
        if len(slash_split) == 2:
            return float(slash_split[0]) / float(slash_split[1])
        else:
            return float(num_str)
    except ValueError:
        return 0