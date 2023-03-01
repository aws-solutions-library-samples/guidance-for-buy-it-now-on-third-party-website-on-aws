#!/usr/bin/env python3

import aws_cdk as cdk
from aws_cdk import Aspects
from cdk_nag import AwsSolutionsChecks

from guidance_for_buy_it_now_on_third_party_website_on_aws.guidance_for_buy_it_now_on_third_party_website_on_aws_stack import GuidanceForBuyItNowOnThirdPartyWebsiteOnAwsStack
from guidance_for_buy_it_now_on_third_party_website_on_aws.guidance_mock_stack import RootStack


app = cdk.App()
GuidanceForBuyItNowOnThirdPartyWebsiteOnAwsStack(app, "guidance-for-buy-it-now-on-third-party-website-on-aws")
RootStack(app)
#Aspects.of(app).add(AwsSolutionsChecks())
app.synth()
