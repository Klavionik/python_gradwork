from tempfile import TemporaryFile

import requests
import yaml
from requests.exceptions import RequestException
from rest_framework import permissions
from rest_framework.parsers import FileUploadParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from yaml.error import YAMLError

from .exceptions import ResourceUnavailableError, YAMLParserError, URLError, InvalidDataError
from .forms import PriceListURLForm
from .permissions import SellerPermission
from .serializers import PriceListSerializer


class PriceListUpdateView(APIView):
    class YAMLUploadParser(FileUploadParser):
        media_type = 'text/yaml'

    parser_classes = [JSONParser, YAMLUploadParser]
    permission_classes = [permissions.IsAuthenticated, SellerPermission]

    form = PriceListURLForm
    serializer = PriceListSerializer
    success_message = "Price list updated: %s products"

    def get_url(self):
        form = self.form(self.request.data, shop_url=self.request.user.shop.url)

        if form.is_valid():
            source = form.cleaned_data['url']
            return source
        else:
            raise URLError()

    @staticmethod
    def get_content(source):
        try:
            with TemporaryFile() as f:
                for chunk in source:
                    f.write(chunk)
                f.seek(0)

                price_list = yaml.safe_load(f.read())

                return price_list
        except YAMLError:
            raise YAMLParserError()

    def get_price_list(self, source):
        try:
            content = requests.get(source, stream=True)

            if content.status_code == 200:
                price_list = self.get_content(content.iter_content(
                    chunk_size=512, decode_unicode=True)
                )

                return price_list
            else:
                content.raise_for_status()
        except RequestException:
            raise ResourceUnavailableError()

    def post(self, request, *args, **kwargs):
        if self.request.FILES:
            return self.update_from_file()
        else:
            return self.update_from_url()

    def update_from_url(self):
        source = self.get_url()
        return self.update_prices(self.get_price_list(source))

    def update_from_file(self):
        file = self.request.FILES['file']
        return self.update_prices(self.get_content(file))

    def update_prices(self, price_list):
        serializer = self.serializer(
            data=price_list,
            shop=self.request.user.shop)

        if serializer.is_valid():
            updated = serializer.save()
            return self.success(updated)
        else:
            raise InvalidDataError()

    def success(self, updated):
        msg = {"response": self.success_message % updated}
        return Response(data=msg)
