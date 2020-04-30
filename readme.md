# sample function for decode VicPack messages.

Vicotee Device -> LoraGateway -> Azure IOT Hub -> Azure Function -> Azure Event HUB 

=> Azure Stream Analytics => PowerBI/Database etc.

## requirements

1. Azure IOT hub
2. Azure Functions
3. Azure Event hub

File: local.settings.json

    "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=<CHANGEME>;AccountKey=<CHANGEME>;EndpointSuffix=core.windows.net",
    "IOTHUB":"Endpoint=<CHANGEME>",
    "MyEventHubSendAppSetting":"Endpoint=<CHANGEME>"
  

### Links
- https://docs.microsoft.com/en-us/azure/azure-functions/functions-app-settings