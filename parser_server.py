import json
import logging
import os
from concurrent import futures
from parser.parser_pb2 import Response
from parser.parser_pb2_grpc import ParserServicer, add_ParserServicer_to_server

import grpc
import pandas as pd
from pandera import Check, Column, DataFrameSchema

logging.basicConfig(
    format="[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)


GRPC_PORT = os.environ["GRPC_PORT"]


class Parser(ParserServicer):
    def Parse(self, request, context):
        logging.info("Processing request.")

        try:
            df = process_data(request.data)
            df.to_csv("data/books-data.csv", index=False)
            with open("data/books-data.json", "w") as f:
                f.write(json.dumps(df.to_dict("records"), indent=2))

            logging.info("Finished.")
            return Response(message="OK")

        except Exception as e:
            context.set_details(e)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            logging.error(f"Failed: {e}")
            return Response(message="FAILED")


def process_data(data: str) -> pd.DataFrame:
    # Deserialize string to python object
    data_json = json.loads(data)
    df = pd.DataFrame(data_json)

    # rename columns
    df.columns = [
        "name",
        "upc",
        "product_type",
        "price",
        "price_with_tax",
        "tax",
        "availability",
        "reviews",
    ]

    # remove duplicated entries
    df = (
        df.sort_values(["name", "upc"])
        .drop_duplicates("upc")
        .drop_duplicates("name")
        .reset_index(drop=True)
    )

    # parse and clean data
    df["price"] = df["price"].str.replace("£", "").astype(float)
    df["price_with_tax"] = df["price_with_tax"].str.replace("£", "").astype(float)
    df["tax"] = df["tax"].str.replace("£", "").astype(float)
    df["availability"] = df["availability"].str.extract("(\d+)").astype(int)
    df["reviews"] = df["reviews"].astype(int)

    # validate data quality
    schema = DataFrameSchema(
        {
            "name": Column(str),
            "upc": Column(str),
            "product_type": Column(str, Check.equal_to("Books")),
            "price_with_tax": Column(float, Check.greater_than(0)),
            "price": Column(float, Check.greater_than(0)),
            "tax": Column(float, Check.greater_than_or_equal_to(0)),
            "availability": Column(int, Check.greater_than_or_equal_to(0)),
            "reviews": Column(int, Check.greater_than_or_equal_to(0)),
        },
        unique=["name", "upc"],
    )
    schema.validate(df)

    return df


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_ParserServicer_to_server(Parser(), server)
    server.add_insecure_port("[::]:" + GRPC_PORT)
    server.start()
    logging.info("Parser service started, listening on " + GRPC_PORT)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
