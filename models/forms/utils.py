from typing import List

from django.forms import BaseForm


def errors_to_messages(form: BaseForm) -> List[str]:
    error_list = []
    for field, field_errors in form.errors.items():
        if field == "__all__":
            error_list.extend(str(e) for e in field_errors)
        else:
            field_label = form.fields[field].label
            error_list.extend(f"{field_label}: {e}" for e in field_errors)
    return error_list
