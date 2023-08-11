from django import forms


class ServiceForm(forms.Form):
    container_ref = forms.CharField(
        label="Container Image Reference", max_length=1000)
    is_public = forms.BooleanField(label="Public", required=False)


class ApplicationForm(forms.Form):
    name = forms.CharField(label="Name", max_length=200)
    description = forms.CharField(
        label="Description", max_length=2000,
        widget=forms.Textarea(attrs={"rows": "4"}))
    environment = forms.JSONField(label="environment variables")
    is_public = forms.BooleanField(label="Public", required=False)

    def __init__(self, *args, **kwargs):
        services = kwargs.pop("services")
        super().__init__(*args, **kwargs)

        self.fields["services"] = forms.MultipleChoiceField(
            choices=[(s["uuid"], s["container_ref"]) for s in services],
            widget=forms.CheckboxSelectMultiple(),
        )


class JobForm(forms.Form):
    environment = forms.JSONField(label="environment variables")
    is_public = forms.BooleanField(label="Public", required=False)
    timings = forms.CharField(
        label="Timing strings", max_length=2000,
        widget=forms.Textarea(attrs={"rows": "4"}))

    def __init__(self, *args, **kwargs):
        applications = kwargs.pop("applications")
        devices = kwargs.pop("devices")
        super().__init__(*args, **kwargs)

        self.fields["application"] = forms.ChoiceField(
            choices=[(s["uuid"], s["name"]) for s in applications],
        )
        self.fields["devices"] = forms.MultipleChoiceField(
            choices=[(s["uuid"], s["device_name"]) for s in devices],
            widget=forms.CheckboxSelectMultiple(),
        )
