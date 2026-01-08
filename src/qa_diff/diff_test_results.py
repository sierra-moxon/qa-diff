"""Create a list of tests that pass in CI but fail in Dev."""

import csv
import json
import os
from typing import Tuple

import httpx

from qa_diff.shared import (
    recursive_get_auxgraph_edges,
    recursive_get_edge_support_graphs,
)

ARS_CI_URL = "https://ars.ci.transltr.io/ars/api/messages"
ARS_DEV_URL = "https://ars-dev.transltr.io/ars/api/messages"
NODE_NORM_URL = {
    "dev": "https://nodenormalization-sri.renci.org/1.4",
    "ci": "https://nodenorm.ci.transltr.io",
    "test": "https://nodenorm.test.transltr.io/1.4",
    "prod": "https://nodenorm.transltr.io/1.4",
}


def get_test_diffs(dev_result_path: str, ci_result_path: str) -> None:
    """Analyze the difference between two automated test results.

    Currently, this just looks at data source disparity, but one could ideally
    adapt it and look at other aspects of each result.

    Args:
        dev_result_path: str - the local path to an automated test csv output file.
        ci_result_path: str - the local path to an automated test csv output file.
    """
    dev_results = {}
    with open(dev_result_path, encoding="utf-8") as f:
        csv_reader = csv.reader(f)
        columns = next(csv_reader)
        for row in csv_reader:
            row_dict = dict(zip(columns, row))
            dev_results[row_dict["TestAsset"]] = row_dict

    ci_results = {}
    with open(ci_result_path, encoding="utf-8") as f:
        csv_reader = csv.reader(f)
        columns = next(csv_reader)
        for row in csv_reader:
            row_dict = dict(zip(columns, row))
            ci_results[row_dict["TestAsset"]] = row_dict

    diff_results = {}
    for test_asset, results in ci_results.items():
        if (
            results["ars"] == "PASSED" and (
                dev_results[test_asset]["ars"] == "FAILED" or
                dev_results[test_asset]["ars"] == "DONE" or
                dev_results[test_asset]["ars"] == "No results"
            )
        ):
            diff_results[test_asset] = {
                "ci": {
                    **results,
                },
                "dev": {
                    **dev_results[test_asset]
                },
            }

    print(f"{len(diff_results.keys())} failed tests.")
    with open("test_diffs/diff_test_results.json", "w", encoding="utf-8") as f:
        json.dump(diff_results, f, indent=2)

    sources = []
    for asset_id, result in diff_results.items():
        asset = get_test_asset(asset_id)
        if (
            asset["expected_output"] != "TopAnswer" and
            asset["expected_output"] != "Acceptable"
        ):
            continue
        print(asset_id)
        ci_pk, dev_pk = get_pks(result)
        ci_response_path = f"test_diffs/{asset_id}_ars_response_ci.json"
        if not os.path.exists(ci_response_path):
            ci_response = get_response_from_ars(ARS_CI_URL, ci_pk)
            with open(ci_response_path, "w", encoding="utf-8") as f:
                json.dump(ci_response, f, indent=2)
        else:
            with open(ci_response_path, "r", encoding="utf-8") as f:
                ci_response = json.load(f)
        dev_response_path = f"test_diffs/{asset_id}_ars_response_dev.json"
        if not os.path.exists(dev_response_path):
            dev_response = get_response_from_ars(ARS_DEV_URL, dev_pk)
            with open(dev_response_path, "w", encoding="utf-8") as f:
                json.dump(dev_response, f, indent=2)
        else:
            with open(dev_response_path, "r", encoding="utf-8") as f:
                dev_response = json.load(f)
        normalized_curie = normalize_curie(asset["output_id"])
        found_result = False
        for result in ci_response["message"]["results"]:
            if found_result:
                break
            for node_bindings in result["node_bindings"]:
                if found_result:
                    break
                for node_binding in result["node_bindings"][node_bindings]:
                    if found_result:
                        break
                    if node_binding["id"] == normalized_curie:
                        ci_single_result = build_kg_from_result(result, ci_response)
                        with open(
                            f"test_diffs/{asset_id}_ci_single_result.json",
                            "w",
                            encoding="utf-8"
                        ) as f:
                            json.dump(ci_single_result, f, indent=2)
                        for edge in ci_single_result["edges"].values():
                            for source in edge["sources"]:
                                if source["resource_role"] == "primary_knowledge_source":
                                    sources.append(source["resource_id"])
                        found_result = True

    with open("test_diffs/missing_sources.json", "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2)

    source_counts = {}
    for source in sources:
        source_counts[source] = source_counts.get(source, 0) + 1

    with open("test_diffs/missing_source_counts.json", "w", encoding="utf-8") as f:
        json.dump(source_counts, f, indent=2)


def extract_edge_details(edge: dict, edge_id: str, target_infores: str = None) -> dict:
    """Extract detailed information from an edge for reporting.
    
    Args:
        edge: dict - the edge object from the knowledge graph
        edge_id: str - the edge identifier
        target_infores: str - optional infores to filter sources
    
    Returns:
        dict with edge details including subject, predicate, object, sources, and qualifiers
    """
    primary_sources = []
    aggregator_sources = []
    
    for source in edge.get("sources", []):
        source_id = source.get("resource_id")
        if target_infores and source_id != target_infores:
            continue
        
        source_info = {
            "resource_id": source_id,
            "resource_role": source.get("resource_role"),
        }
        if "upstream_resource_ids" in source:
            source_info["upstream_resource_ids"] = source["upstream_resource_ids"]
        
        if source.get("resource_role") == "primary_knowledge_source":
            primary_sources.append(source_info)
        elif source.get("resource_role") == "aggregator_knowledge_source":
            aggregator_sources.append(source_info)
    
    edge_detail = {
        "edge_id": edge_id,
        "subject": edge.get("subject"),
        "predicate": edge.get("predicate"),
        "object": edge.get("object"),
        "primary_knowledge_sources": primary_sources,
        "aggregator_knowledge_sources": aggregator_sources,
    }
    
    if "qualifiers" in edge and edge["qualifiers"]:
        edge_detail["qualifiers"] = edge["qualifiers"]
    
    return edge_detail


def compare_infores_sources(dev_result_path: str, ci_result_path: str, infores_filter: str = None) -> None:
    """Compare infores sources between CI and Dev for specific test assets.
    
    Args:
        dev_result_path: str - the local path to an automated test csv output file.
        ci_result_path: str - the local path to an automated test csv output file.
        infores_filter: str - optional infores to filter (e.g., 'infores:gtopdb')
    """
    dev_results = {}
    with open(dev_result_path, encoding="utf-8") as f:
        csv_reader = csv.reader(f)
        columns = next(csv_reader)
        for row in csv_reader:
            row_dict = dict(zip(columns, row))
            dev_results[row_dict["TestAsset"]] = row_dict

    ci_results = {}
    with open(ci_result_path, encoding="utf-8") as f:
        csv_reader = csv.reader(f)
        columns = next(csv_reader)
        for row in csv_reader:
            row_dict = dict(zip(columns, row))
            ci_results[row_dict["TestAsset"]] = row_dict

    diff_results = {}
    for test_asset, results in ci_results.items():
        if (
            results["ars"] == "PASSED" and (
                dev_results[test_asset]["ars"] == "FAILED" or
                dev_results[test_asset]["ars"] == "DONE" or
                dev_results[test_asset]["ars"] == "No results"
            )
        ):
            diff_results[test_asset] = {
                "ci": {
                    **results,
                },
                "dev": {
                    **dev_results[test_asset]
                },
            }

    print(f"{len(diff_results.keys())} failed tests.")
    
    infores_comparison = {}
    detailed_edges_by_infores = {}
    
    for asset_id, result in diff_results.items():
        asset = get_test_asset(asset_id)
        if (
            asset["expected_output"] != "TopAnswer" and
            asset["expected_output"] != "Acceptable"
        ):
            continue
        
        print(f"Processing {asset_id}")
        ci_pk, dev_pk = get_pks(result)
        
        ci_response_path = f"test_diffs/{asset_id}_ars_response_ci.json"
        if not os.path.exists(ci_response_path):
            ci_response = get_response_from_ars(ARS_CI_URL, ci_pk)
            with open(ci_response_path, "w", encoding="utf-8") as f:
                json.dump(ci_response, f, indent=2)
        else:
            with open(ci_response_path, "r", encoding="utf-8") as f:
                ci_response = json.load(f)
        
        dev_response_path = f"test_diffs/{asset_id}_ars_response_dev.json"
        if not os.path.exists(dev_response_path):
            dev_response = get_response_from_ars(ARS_DEV_URL, dev_pk)
            with open(dev_response_path, "w", encoding="utf-8") as f:
                json.dump(dev_response, f, indent=2)
        else:
            with open(dev_response_path, "r", encoding="utf-8") as f:
                dev_response = json.load(f)
        
        ci_sources = set()
        dev_sources = set()
        ci_edges_by_infores = {}
        dev_edges_by_infores = {}
        
        for edge_id, edge in ci_response.get("message", {}).get("knowledge_graph", {}).get("edges", {}).items():
            for source in edge.get("sources", []):
                if source.get("resource_role") == "primary_knowledge_source":
                    source_id = source.get("resource_id")
                    if infores_filter is None or source_id == infores_filter:
                        ci_sources.add(source_id)
                        if source_id not in ci_edges_by_infores:
                            ci_edges_by_infores[source_id] = []
                        ci_edges_by_infores[source_id].append(extract_edge_details(edge, edge_id, source_id))
        
        for edge_id, edge in dev_response.get("message", {}).get("knowledge_graph", {}).get("edges", {}).items():
            for source in edge.get("sources", []):
                if source.get("resource_role") == "primary_knowledge_source":
                    source_id = source.get("resource_id")
                    if infores_filter is None or source_id == infores_filter:
                        dev_sources.add(source_id)
                        if source_id not in dev_edges_by_infores:
                            dev_edges_by_infores[source_id] = []
                        dev_edges_by_infores[source_id].append(extract_edge_details(edge, edge_id, source_id))
        
        only_in_ci = ci_sources - dev_sources
        only_in_dev = dev_sources - ci_sources
        in_both = ci_sources & dev_sources
        
        if only_in_ci or only_in_dev:
            infores_comparison[asset_id] = {
                "only_in_ci": sorted(list(only_in_ci)),
                "only_in_dev": sorted(list(only_in_dev)),
                "in_both": sorted(list(in_both)),
            }
            
            for infores in only_in_ci:
                if infores not in detailed_edges_by_infores:
                    detailed_edges_by_infores[infores] = {}
                detailed_edges_by_infores[infores][asset_id] = ci_edges_by_infores.get(infores, [])
    
    output_file = "test_diffs/infores_comparison.json"
    if infores_filter:
        output_file = f"test_diffs/infores_comparison_{infores_filter.replace(':', '_')}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(infores_comparison, f, indent=2)
    
    summary = {}
    for asset_id, comparison in infores_comparison.items():
        for source in comparison["only_in_ci"]:
            if source not in summary:
                summary[source] = {"count": 0, "test_assets": []}
            summary[source]["count"] += 1
            summary[source]["test_assets"].append(asset_id)
    
    summary_file = "test_diffs/infores_only_in_ci_summary.json"
    if infores_filter:
        summary_file = f"test_diffs/infores_only_in_ci_summary_{infores_filter.replace(':', '_')}.json"
    
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    detailed_summary_file = "test_diffs/infores_edges_only_in_ci_detailed.json"
    if infores_filter:
        detailed_summary_file = f"test_diffs/infores_edges_only_in_ci_detailed_{infores_filter.replace(':', '_')}.json"
    
    with open(detailed_summary_file, "w", encoding="utf-8") as f:
        json.dump(detailed_edges_by_infores, f, indent=2)
    
    tsv_file = "test_diffs/infores_edges_only_in_ci_detailed.tsv"
    if infores_filter:
        tsv_file = f"test_diffs/infores_edges_only_in_ci_detailed_{infores_filter.replace(':', '_')}.tsv"
    
    with open(tsv_file, "w", encoding="utf-8") as f:
        f.write("\t".join([
            "infores",
            "test_asset",
            "edge_id",
            "subject",
            "predicate",
            "object",
            "primary_knowledge_source",
            "aggregator_knowledge_source",
            "object_direction_qualifier",
            "object_aspect_qualifier",
            "qualified_predicate"
        ]) + "\n")
        
        for infores, test_assets in detailed_edges_by_infores.items():
            for test_asset, edges in test_assets.items():
                for edge in edges:
                    primary_sources = "|".join([s["resource_id"] for s in edge.get("primary_knowledge_sources", [])])
                    aggregator_sources = "|".join([s["resource_id"] for s in edge.get("aggregator_knowledge_sources", [])])
                    
                    object_direction = ""
                    object_aspect = ""
                    qualified_predicate = ""
                    
                    for qualifier in edge.get("qualifiers", []):
                        qtype = qualifier.get("qualifier_type_id", "")
                        qvalue = qualifier.get("qualifier_value", "")
                        
                        if qtype == "biolink:object_direction_qualifier":
                            object_direction = qvalue
                        elif qtype == "biolink:object_aspect_qualifier":
                            object_aspect = qvalue
                        elif qtype == "biolink:qualified_predicate":
                            qualified_predicate = qvalue
                    
                    f.write("\t".join([
                        infores,
                        test_asset,
                        edge.get("edge_id", ""),
                        edge.get("subject", ""),
                        edge.get("predicate", ""),
                        edge.get("object", ""),
                        primary_sources,
                        aggregator_sources,
                        object_direction,
                        object_aspect,
                        qualified_predicate
                    ]) + "\n")
    
    print(f"\nSources only in CI (not in Dev):")
    for source, data in sorted(summary.items(), key=lambda x: x[1]["count"], reverse=True):
        print(f"  {source}: {data['count']} test assets")
    
    if detailed_edges_by_infores:
        print(f"\nDetailed edge information saved to:")
        print(f"  JSON: {detailed_summary_file}")
        print(f"  TSV:  {tsv_file}")


def export_trapi_responses(dev_result_path: str, ci_result_path: str) -> None:
    """Export all TRAPI responses for tests that pass in CI but fail in Dev.
    
    Args:
        dev_result_path: str - the local path to an automated test csv output file.
        ci_result_path: str - the local path to an automated test csv output file.
    """
    dev_results = {}
    with open(dev_result_path, encoding="utf-8") as f:
        csv_reader = csv.reader(f)
        columns = next(csv_reader)
        for row in csv_reader:
            row_dict = dict(zip(columns, row))
            dev_results[row_dict["TestAsset"]] = row_dict

    ci_results = {}
    with open(ci_result_path, encoding="utf-8") as f:
        csv_reader = csv.reader(f)
        columns = next(csv_reader)
        for row in csv_reader:
            row_dict = dict(zip(columns, row))
            ci_results[row_dict["TestAsset"]] = row_dict

    diff_results = {}
    for test_asset, results in ci_results.items():
        if (
            results["ars"] == "PASSED" and (
                dev_results[test_asset]["ars"] == "FAILED" or
                dev_results[test_asset]["ars"] == "DONE" or
                dev_results[test_asset]["ars"] == "No results"
            )
        ):
            diff_results[test_asset] = {
                "ci": {
                    **results,
                },
                "dev": {
                    **dev_results[test_asset]
                },
            }

    print(f"{len(diff_results.keys())} tests pass in CI but fail in Dev.")
    
    trapi_responses = {}
    
    for asset_id, result in diff_results.items():
        asset = get_test_asset(asset_id)
        if (
            asset["expected_output"] != "TopAnswer" and
            asset["expected_output"] != "Acceptable"
        ):
            continue
        
        print(f"Processing {asset_id}")
        ci_pk, dev_pk = get_pks(result)
        
        ci_response_path = f"test_diffs/{asset_id}_ars_response_ci.json"
        if not os.path.exists(ci_response_path):
            ci_response = get_response_from_ars(ARS_CI_URL, ci_pk)
            with open(ci_response_path, "w", encoding="utf-8") as f:
                json.dump(ci_response, f, indent=2)
        else:
            with open(ci_response_path, "r", encoding="utf-8") as f:
                ci_response = json.load(f)
        
        dev_response_path = f"test_diffs/{asset_id}_ars_response_dev.json"
        if not os.path.exists(dev_response_path):
            dev_response = get_response_from_ars(ARS_DEV_URL, dev_pk)
            with open(dev_response_path, "w", encoding="utf-8") as f:
                json.dump(dev_response, f, indent=2)
        else:
            with open(dev_response_path, "r", encoding="utf-8") as f:
                dev_response = json.load(f)
        
        trapi_responses[asset_id] = {
            "ci_response": ci_response,
            "dev_response": dev_response
        }
    
    output_file = "test_diffs/trapi_responses_ci_pass_dev_fail.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(trapi_responses, f, indent=2)
    
    print(f"\nTRAPI responses saved to {output_file}")
    print(f"Total test assets: {len(trapi_responses)}")


def normalize_curie(curie: str) -> str:
    """Normalize a list of curies."""
    node_norm = NODE_NORM_URL["ci"]

    with httpx.Client() as client:
        try:
            response = client.post(
                node_norm + "/get_normalized_nodes",
                json={
                    "curies": [curie],
                    "conflate": True,
                    "drug_chemical_conflate": True,
                },
            )
            response.raise_for_status()
            response = response.json()
            for curie, attrs in response.items():
                if attrs is None:
                    return curie
                else:
                    return attrs["id"]["identifier"]
        except httpx.RequestError as e:
            print(f"Node norm failed with: {e}")
            print("Using original curies.")
    return curie


def get_test_asset(asset_id: str) -> dict:
    """Get a test asset json from github."""
    with httpx.Client(timeout=60) as client:
        response = client.get(f"https://raw.githubusercontent.com/NCATSTranslator/Tests/main/test_assets/{asset_id}.json")
        response.raise_for_status()
        asset_dict = response.json()
        return asset_dict


def get_pks(test_result: dict) -> Tuple[str, str]:
    """Get the pk from a test result dict."""
    ci_url = test_result["ci"]["pk"]
    dev_url = test_result["dev"]["pk"]

    return (
        ci_url.split("=")[-1],
        dev_url.split("=")[-1]
    )


def get_response_from_ars(ars_url: str, pk: str) -> dict:
    """Get a full TRAPI message from ARS."""
    print("Getting response from ARS.")
    with httpx.Client(timeout=60) as client:
        response = client.get(f"{ars_url}/{pk}")
        response.raise_for_status()
        response = response.json()
        merged_version = response["fields"]["merged_version"]
        print("Got merged version pk, getting response.")

        response = client.get(f"{ars_url}/{merged_version}")
        response.raise_for_status()
        response = response.json()
        print("Got ARS merged version response.")
        return response["fields"]["data"]


def build_kg_from_result(result: dict, response: dict):
    """Given a response, build a kg from the result."""
    message_auxgraphs = response.get("message", {}).get("auxiliary_graphs", {})
    kg_edges = (
        response.get("message", {}).get("knowledge_graph", {}).get("edges", {})
    )
    nodes = set()
    edges = set()
    auxgraphs = set()
    temp_auxgraphs = set()
    temp_edges = set()
    for _, knodes in result.get("node_bindings", {}).items():
        nodes.update([k["id"] for k in knodes])
    for analysis in result.get("analyses", []):
        for _, kedges in analysis.get("edge_bindings", {}).items():
            temp_edges.update([k["id"] for k in kedges])
        for _, path_graphs in analysis.get("path_bindings", {}).items():
            temp_auxgraphs.update(a["id"] for a in path_graphs)
    for analysis in result.get("analyses", []):
        for auxgraph in analysis.get("support_graphs", []):
            temp_auxgraphs.add(auxgraph)
    for edge in temp_edges:
        try:
            edges, auxgraphs, nodes = recursive_get_edge_support_graphs(
                edge,
                edges,
                auxgraphs,
                kg_edges,
                message_auxgraphs,
                nodes,
            )
        except KeyError as e:
            print(f"Failed to get edge support graph {edge}: {e}")
            continue
    for auxgraph in temp_auxgraphs:
        try:
            edges, auxgraphs, nodes = recursive_get_auxgraph_edges(
                auxgraph,
                edges,
                auxgraphs,
                kg_edges,
                message_auxgraphs,
                nodes,
            )
        except KeyError as e:
            print(f"Failed to get auxgraph edges {auxgraph}: {e}")
            continue

    single_result = {"nodes": {}, "edges": {}}
    kg_nodes = (
        response.get("message", {}).get("knowledge_graph", {}).get("nodes", {})
    )
    single_result["nodes"] = {
        nid: ndata for nid, ndata in kg_nodes.items() if nid in nodes
    }
    kg_edges = (
        response.get("message", {}).get("knowledge_graph", {}).get("edges", {})
    )
    single_result["edges"] = {
        eid: edata for eid, edata in kg_edges.items() if eid in edges
    }

    return single_result
