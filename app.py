#!/usr/bin/env python3
import os

import aws_cdk as cdk

from chatCDK.cdk_stack import CouchbaseChatStack
from ingestCDK.cdk_stack import CouchbaseIngestStack


app = cdk.App()
CouchbaseIngestStack(app, "CouchbaseBedrockStack")
CouchbaseChatStack(app, "CouchbaseChatStack")

app.synth()
