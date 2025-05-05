from django import forms

from models.models import Person


class PersonForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rut'].required = False

    class Meta:
        model = Person
        fields = (
            'name',
            'last_name',
            'email',
            'phone',
            'rut',
        )
