from django import forms


class PriceListURLForm(forms.Form):
    url = forms.URLField()

    def __init__(self, *args, **kwargs):
        self.shop_url = kwargs.pop('shop_url')
        super().__init__(*args, **kwargs)

    def clean_url(self):
        url = self.cleaned_data['url']
        if self.shop_url not in url:
            raise forms.ValidationError("Price list must be uploaded from the shop's URL")
        return url
