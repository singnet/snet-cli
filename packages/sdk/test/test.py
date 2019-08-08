from snet.sdk import SnetSDK

from config import config

sdk = SnetSDK(config)

# Examples using the "get_method" utility function
service_client = sdk.create_dynamic_service_client("snet", "example-service")

method, request_type, _ = service_client.get_method("add")
request = request_type(a=20, b=3)
print("Performing {} + {}:".format(request.a, request.b))
result = method(request)
print("Result: {}".format(result.value))

# Example using the "get_method" utility function and a fully qualified method name ([<package>].service.method)
method, request_type, _ = service_client.get_method("example_service.Calculator.mul")
request = request_type(a=7, b=12)
print("Performing {} * {}:".format(request.a, request.b))
result = method(request)
print("Result: {}".format(result.value))


# Examples without the get_method utility function
service_client = sdk.create_dynamic_service_client("snet", "i3d-video-action-recognition")
request = service_client.message.Input(model="400", url="http://crcv.ucf.edu/THUMOS14/UCF101/UCF101/v_CricketShot_g04_c02.avi")
print("Performing video action recognition")
result = service_client.service.VideoActionRecognition.service.video_action_recon(request)
print("Result: {}".format(result))


service_client = sdk.create_dynamic_service_client("snet", "cntk-image-recon")
request = service_client.message.Input(model="ResNet152", img_path="https://www.fiftyflowers.com/site_files/FiftyFlowers/Image/Product/Mini-Black-Eye-bloom-350_c7d02e72.jpg")
print("Performing image recognition")
result = service_client.service.Recognizer.service.flowers(request)
print("Result: {}".format(result))
