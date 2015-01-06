def filesizeformat(num):
    for size in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.2f%s" % (num, size)
        num /= 1024.0
    return "%3.2f%s" % (num, 'TB')


def bytes_to_gb(orig_bytes):
    return "%3.6f" % (orig_bytes / float(1024 * 1024 * 1024))


def get_days_elapsed(created, deleted, start, end):
    if start > end:
        raise ImproperlyConfigured("Start date must be becore the end date")
    actual_start = start
    actual_end = end
    # Camp reduce period if created or deleted within
    if created > start:
        actual_start = created
    if deleted and deleted < end:
        actual_end = end
    return (actual_end - actual_start).days


def get_usage(shape_row, start, end):
    days = get_days_elapsed(shape_row['item__created'],
                            shape_row['deleted'],
                            start, end)
    return bytes_to_gb(shape_row['size'] * days)
