def get_signage(edge_data):
    is_ows = edge_data['one_way']
    is_ows_reversed = edge_data['one_way_reversed']

    if is_ows:
        return "go"
    elif is_ows_reversed:
        return "stop"
    else:
        return None


def get_crowdedness(edge_data):
    density_on_edge = edge_data['density']
    if density_on_edge >= 1.5:
        return 3
    elif 0.5 <= density_on_edge < 1.5:
        return 2
    elif 0 < density_on_edge < 0.5:
        return 1
    else:
        return None
