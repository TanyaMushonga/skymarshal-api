from unittest.mock import patch, MagicMock
from apps.vehicle_lookup.views import VehicleRegistrationViewSet
from django.test import RequestFactory
from apps.users.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
import json

def verify_alpr_logic():
    factory = RequestFactory()
    image_content = b'fake-image-binary-content'
    image = SimpleUploadedFile('test.jpg', image_content, content_type='image/jpeg')
    request = factory.post('/api/vehicles/lookup/', {'image': image})

    try:
        user = User.objects.get(email='tanyaradzwatmushonga@gmail.com')
    except User.DoesNotExist:
        user = User.objects.first()
        
    request.user = user

    with patch('apps.vehicle_lookup.views.LicensePlateReader') as mock_reader_cls:
        mock_reader = mock_reader_cls.return_value
        mock_reader.detect_and_read.return_value = 'KBA800D'
        view = VehicleRegistrationViewSet.as_view({'post': 'lookup'})
        response = view(request)
        print(f'Status: {response.status_code}')
        print(f'Resolved Plate: {response.data.get("resolved_plate")}')
        print(f'Vehicle Found: {bool(response.data.get("vehicle"))}')

if __name__ == "__main__":
    verify_alpr_logic()
