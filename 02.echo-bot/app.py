# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import sys
import traceback
from datetime import datetime
from http import HTTPStatus

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    TurnContext,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.schema import Activity, ActivityTypes

from bots import EchoBot
from config import DefaultConfig

from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient


CONFIG = DefaultConfig()
#2025/03/23 - START Extended for PravalikaTesting Project in MSAI-631-B01 adding sentiment analysis to the bot
credential = AzureKeyCredential(CONFIG.API_KEY)
endpointURI = CONFIG.ENDPOINT_URI
text_analytics_client = TextAnalyticsClient(endpoint=endpointURI, credential=credential)
##2025/03/23 - STOP Extended for PravalikaTesting Project in MSAI-631-B01


# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
ADAPTER = CloudAdapter(ConfigurationBotFrameworkAuthentication(CONFIG))


# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )
    # Send a trace activity if we're talking to the Bot Framework Emulator
    if context.activity.channel_id == "emulator":
        # Create a trace activity that contains the error object
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        # Send a trace activity, which will be displayed in Bot Framework Emulator
        await context.send_activity(trace_activity)


ADAPTER.on_turn_error = on_error

# Create the Bot
BOT = EchoBot()


# Listen for incoming requests on /api/messages
# async def messages(req: Request) -> Response:
#     if "application/json" in req.headers["Content-Type"]:
#         body = await req.json()

#         #start reverse string
#         print(body)
#         reversed_text = body["text"][::-1]
#         body["text"]= reversed_text
#         print(body)
#         #end reverse string
#     else:
#         return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)


#     return await ADAPTER.process(req, BOT)
async def messages(req: Request) -> Response:
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()

        # 2025/3/23 - MSAI-631-B01 - start perform Sentiment Analysis Here
        textToUse = body["text"]
        print(f"textTouse = {textToUse}")
        documents = [{"id":"1", "language": "en", "text":body["text"]}]
        response = text_analytics_client.analyze_sentiment(documents)
        successful_responses = [doc for doc in response if not doc.is_error]
        body["text"] = successful_responses
        print(successful_responses)
        # 2025/03/23 - MSAI 631-B01 -END Perform Sentiment Analysis Here
    else:
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    # Create an activity response with sentiment result
    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    response = await ADAPTER.process_activity(auth_header, activity, BOT.on_turn)

APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    try:
        web.run_app(APP, host="localhost", port=CONFIG.PORT)
    except Exception as error:
        raise error
