from django.core.paginator import Paginator


SCHEDULE_PAGE_SIZE = 18


def get_requested_schedule_page(value) -> int:
    try:
        page = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, page)


def paginate_schedule(schedule_rows, requested_page: int, page_size: int = SCHEDULE_PAGE_SIZE):
    paginator = Paginator(schedule_rows, page_size)
    return paginator.get_page(requested_page)
