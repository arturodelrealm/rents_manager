import time
import logging
from django.db import connection

logger = logging.getLogger(__name__)


class QueryCountMiddleware:
    MINIMUM_QUERIES_TO_LOG = 10

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        initial_queries = len(connection.queries)
        start = time.time()
        response = self.get_response(request)
        total_time = time.time() - start

        num_queries = len(connection.queries) - initial_queries
        if num_queries > self.MINIMUM_QUERIES_TO_LOG:
            logger.info(
                f"[SQL] {request.method} {request.path} made "
                f"{num_queries} queries in {total_time:.2f}s"
            )

        return response
