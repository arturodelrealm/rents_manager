from operator import attrgetter
from typing import Tuple

from import_export.resources import Resource

from django.utils.translation import gettext_lazy as _
from import_export.results import RowResult, Error
from result import Result, Ok, Err

from .mappings import price_update_frequency_mapping
from models.forms import PersonForm, ImportApartmentForm, ImportContractForm
from models.forms.utils import errors_to_messages
from models.models import Person, Apartment, Contract


class BasicError(Error):

    def traceback(self):
        return ''


class UnifiedContractResource(Resource):

    DIFF_HEADERS = (
        _('Propietario'),
        _('Departamento'),
        _('Arrendatario'),
        _('Precio'),
    )

    FILE_HEADERS = (
        "Propietario nombre",
        "Propietario apellido",
        "Email propietario",
        "Teléfono propietario",
        "Rut propietario",
        "Dirección",
        "Comuna",
        "Arrendatario nombre",
        "Arrendatario apellido",
        "Arrendatario email",
        "Arrendatario teléfono",
        "Arrendatario (2) nombre",
        "Arrendatario (2) apellido",
        "Arrendatario (2) email",
        "Arrendatario (2) teléfono",
        "Precio",
        "Tipo IPC",
        "Fecha inicial",
        "Proximo ajuste",
    )

    def __init__(self, **kwargs):

        super().__init__(**kwargs)
        self.persons_by_email = {
            person.email: person for person in Person.objects.all()
        }
        self.apartments_by_address = {
            apartment.cleaned_address: apartment
            for apartment in Apartment.objects.all()
        }
        self.cached_rows = []

    def _validate_person(self, data: dict) -> Result:
        if data['email'] in self.persons_by_email:
            return Ok(self.persons_by_email[data['email']])
        form = PersonForm(data)
        if form.is_valid():
            # IMPORTANT: don't save the instance until all validations are done
            person = form.save(commit=False)
            self.persons_by_email[person.email] = person
            return Ok(person)
        return Err(errors_to_messages(form))

    def _validate_apartment(self, data: dict) -> Result:
        address = Apartment.clean_address(data['address'])
        if address in self.apartments_by_address:
            apartment = self.apartments_by_address[address]
            # Case when an apartment is already added
            if not apartment.pk:
                return Err([_('Propiedad duplicada en la importación.')])
            return Ok(apartment)
        form = ImportApartmentForm(data)
        if form.is_valid():
            # IMPORTANT: don't save the instance until all validations are done
            apartment = form.save(commit=False)
            self.apartments_by_address[address] = apartment
            return Ok(apartment)
        return Err(errors_to_messages(form))

    @staticmethod
    def get_display_name() -> str:
        return _('Contratos')

    def _validate_dataset(self, dataset) -> Result:
        missing_headers = set(self.FILE_HEADERS).difference(dataset.headers)
        if missing_headers:
            error_message = _(
                'Los siguientes encabezados no se encuentran en el archivo: '
                '{}. Se recomienda descargar el archivo de ejemplo para '
                'evitar errores.'
            ).format(', '.join(missing_headers))
            return Err([error_message])
        return Ok(dataset)

    def import_data_inner(
        self,
        dataset,
        dry_run,
        raise_errors,
        using_transactions,
        collect_failed_rows,
        **kwargs,
    ):
        result = self.get_result_class()()
        result.diff_headers = self.DIFF_HEADERS
        dataset_validation = self._validate_dataset(dataset)
        if dataset_validation.is_err():
            for error in dataset_validation.err():
                result.append_base_error(BasicError(error))
            return result
        result.total_rows = len(dataset)

        for i, row in enumerate(dataset.dict, 1):
            kwargs.update(
                {
                    "dry_run": dry_run,
                    "using_transactions": using_transactions,
                    "row_number": i,
                }
            )
            row_result = self.import_row(
                row,
                **kwargs,
            )
            if row_result.errors:
                result.append_error_row(i, row, row_result.errors)
            result.append_row_result(row_result)
            result.increment_row_result_total(row_result)
        # if result has errors, return it
        if result.has_errors():
            return result
        if not dry_run:
            for row_data in self.cached_rows:
                self.save_row(row_data)
        return result

    def validate_row(self, row) -> Result:
        errors = []
        owner = None
        apartment = None
        tenants = []

        result = self._validate_person({
            "name": row["Propietario nombre"],
            "last_name": row["Propietario apellido"],
            "email": row["Email propietario"],
            "phone": row["Teléfono propietario"],
            "rut": row["Rut propietario"],
        })
        if result.is_err():
            errors.append(_('Propietario inválido: {}.').format(result.err()))
        else:
            owner = result.ok()

        result = self._validate_apartment({
            "address": row["Dirección"],
            "commune": row["Comuna"],
        })
        if result.is_err():
            errors.append(_('Departamento inválido: {}.').format(result.err()))
        else:
            apartment = result.ok()

        for suffix in ["", " (2)"]:
            name = row.get(f"Arrendatario{suffix} nombre".strip())
            if name:
                result = self._validate_person(
                    {
                        "name": name,
                        "last_name": row[f"Arrendatario{suffix} apellido"],
                        "email": row[f"Arrendatario{suffix} email".strip()],
                        "phone": row[f"Arrendatario{suffix} teléfono".strip()]
                    }
                )
                if result.is_err():
                    errors.append(
                        _('Arrendatario{} inválido: {}.').format(
                            suffix,
                            result.err()
                        )
                    )
                else:
                    tenants.append(result.ok())
        if not tenants:
            errors.append(_('No se proporcionaron arrendatarios.'))
        if owner and owner.email in map(attrgetter('email'), tenants):
            errors.append(
                _('El propietario no puede ser también arrendatario.')
            )

        # Quick return if any independent validation fail
        if errors:
            return Err(errors)
        raw_price_update_freq = row.get("Tipo IPC") or ''
        price_update_freq = price_update_frequency_mapping.get(
            raw_price_update_freq.lower(),
            raw_price_update_freq  # Don't lower this in case is already in a
                                   # good format (3M)
        )
        contract_form = ImportContractForm({
            "price": row["Precio"],
            "price_update_frequency": price_update_freq,
            "start_date": row.get("Fecha inicial"),
            "next_price_update": row.get("Proximo ajuste"),
        })
        if not contract_form.is_valid():
            errors.append(
                _("Contrato inválido: {}").format(errors_to_messages(
                    contract_form))
            )

        if errors:
            return Err(errors)
        return Ok(
            {
                'owner': owner,
                'tenants': tenants,
                'apartment': apartment,
                'contract_form': contract_form
            }
        )

    @staticmethod
    def must_skip(data: dict) -> bool:
        apartment = data['apartment']
        return apartment.pk and apartment.active_contracts.exists()

    def import_row(self, row, **kwargs):
        row_result = RowResult()

        validation_result = self.validate_row(row)
        if validation_result.is_err():
            row_result.errors.extend(
                BasicError(error, row=row, number=kwargs['row_number'])
                for error in validation_result.err()
            )
            row_result.import_type = RowResult.IMPORT_TYPE_INVALID
        else:
            data = validation_result.ok()
            if self.must_skip(data):
                row_result.import_type = RowResult.IMPORT_TYPE_SKIP
            else:
                row_result.import_type = RowResult.IMPORT_TYPE_NEW
            self.cached_rows.append((row_result, data))
            # Data to be shown on confirmation
            row_result.diff = (
                data['owner'],
                data['apartment'],
                data['tenants'][0],
                Contract.format_int_price(
                    data['contract_form'].cleaned_data['price']
                )
            )
        return row_result

    @staticmethod
    def save_row(row_data: Tuple[RowResult, dict]):
        row_result, data = row_data
        if row_result.import_type == RowResult.IMPORT_TYPE_SKIP:
            return
        apartment = data['apartment']
        owner = data['owner']
        tenants = data['tenants']
        contract_form = data['contract_form']
        if not owner.pk:
            owner.save()
        if not apartment.pk:
            apartment.save()
        if apartment.owner_id != owner.pk:
            apartment.owner_id = owner.pk
            apartment.save(update_fields=['owner_id'])
        for tenant in tenants:
            if not tenant.pk:
                tenant.save()
        contract = contract_form.save(commit=False)
        contract.apartment = apartment
        contract.save()
        for tenant in tenants:
            contract.tenants.add(tenant)
        contract_form.save_historical_price(contract)
