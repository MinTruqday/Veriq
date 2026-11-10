


class TestabilityBenchmarkObligationScoring:
    """Matching helpers for expected and generated obligations."""

    @staticmethod
    def _maximum_obligation_matching(
        adjacency: list[list[int]], prediction_count: int
    ) -> dict[int, int]:
        expected_count = len(adjacency)
        unmatched = -1
        pair_expected = [unmatched] * expected_count
        pair_prediction = [unmatched] * prediction_count
        distance = [unmatched] * expected_count

        while True:
            queue = []
            for expected_index in range(expected_count):
                if pair_expected[expected_index] == unmatched:
                    distance[expected_index] = 0
                    queue.append(expected_index)
                else:
                    distance[expected_index] = unmatched

            shortest_augmenting_path = None
            queue_index = 0
            while queue_index < len(queue):
                expected_index = queue[queue_index]
                queue_index += 1
                next_distance = distance[expected_index] + 1
                if (
                    shortest_augmenting_path is not None
                    and next_distance > shortest_augmenting_path
                ):
                    continue
                for prediction_index in adjacency[expected_index]:
                    matched_expected = pair_prediction[prediction_index]
                    if matched_expected == unmatched:
                        if shortest_augmenting_path is None:
                            shortest_augmenting_path = next_distance
                    elif distance[matched_expected] == unmatched:
                        distance[matched_expected] = next_distance
                        queue.append(matched_expected)

            if shortest_augmenting_path is None:
                break

            augmented = False
            edge_offsets = [0] * expected_count
            for root_index in range(expected_count):
                if pair_expected[root_index] != unmatched or distance[root_index] != 0:
                    continue
                expected_stack = [root_index]
                path_predictions = []
                while expected_stack:
                    expected_index = expected_stack[-1]
                    descended = False
                    while edge_offsets[expected_index] < len(adjacency[expected_index]):
                        prediction_index = adjacency[expected_index][
                            edge_offsets[expected_index]
                        ]
                        edge_offsets[expected_index] += 1
                        next_distance = distance[expected_index] + 1
                        if next_distance > shortest_augmenting_path:
                            continue
                        matched_expected = pair_prediction[prediction_index]
                        if matched_expected == unmatched:
                            if next_distance != shortest_augmenting_path:
                                continue
                            for path_index, path_expected in enumerate(
                                expected_stack[:-1]
                            ):
                                path_prediction = path_predictions[path_index]
                                pair_expected[path_expected] = path_prediction
                                pair_prediction[path_prediction] = path_expected
                            pair_expected[expected_stack[-1]] = prediction_index
                            pair_prediction[prediction_index] = expected_stack[-1]
                            augmented = True
                            break
                        if distance[matched_expected] == next_distance:
                            path_predictions.append(prediction_index)
                            expected_stack.append(matched_expected)
                            descended = True
                            break
                    if augmented:
                        break
                    if descended:
                        continue
                    distance[expected_index] = unmatched
                    expected_stack.pop()
                    if path_predictions and len(path_predictions) >= len(expected_stack):
                        path_predictions.pop()

            if not augmented:
                break

        return {
            prediction_index: expected_index
            for prediction_index, expected_index in enumerate(pair_prediction)
            if expected_index != unmatched
        }
