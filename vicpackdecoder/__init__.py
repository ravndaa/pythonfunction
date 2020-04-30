import logging
#import vicpack as vic
from . import vicpack as vic #as vic #(explicit relative)

import azure.functions as func


def main(event: func.EventHubEvent) -> str:
    #logging.info('Python EventHub trigger processed an event: %s', event.get_body().decode('utf-8'))
    logging.info('WOPS: %s', event.get_body())
    pack = vic.vicpack()        # instantiate a vicpack class parser
    pack.add(event.get_body().decode('utf-8'))     # add measurement
    pack.detail = True          # when self.__str__ is invoked, print all packet contents
    pack.prefix = False         # do not invoke SI-prefix parser

    print(pack)
    print(pack.export ())
    return "{}".format(pack.export())