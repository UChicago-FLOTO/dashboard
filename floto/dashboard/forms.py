from django import forms


class ServiceForm(forms.Form):
    container_ref = forms.CharField(
        label="Container Image Reference", max_length=1000)
    is_public = forms.BooleanField(label="Public", required=False)
