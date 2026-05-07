"""
Golf Ball Pipeline Tracker

Receives one RF output vector per step and automatically inserts the next ball.
The pipeline holds 4 balls at once.
Expected behavior:
  Step 1: 1 N N N
  Step 2: 2 1 N N
  Step 3: 3 2 1 N
  Step 4: 4 3 2 1
  Step 5: 5 4 3 2

The RF vector is a list of 4 values, e.g. [1, 'X', 'X', 'X'].
Initial frames may be empty and appear as [F, F, F, F].
A ball exiting the pipeline outputs PASS if it was good, FAIL if it was rejected.
"""

class GolfBallPipeline:
    """Tracks golf balls through a 4-slot pipeline."""

    def __init__(self):
        self.slots = [None, None, None, None]
        self.history = []
        self.last_exit = None
        self.next_name = 1
        self.started = False

    def _next_name(self):
        name = str(self.next_name)
        self.next_name += 1
        return name

    def _normalize_value(self, value):
        if isinstance(value, str):
            value = value.strip().upper()
            if value in ['1', 'TRUE', 'P']:
                return 'P'
            if value in ['0', 'X', 'FALSE', 'F', '']:
                return 'F'
        elif value in [1, True]:
            return 'P'
        elif value in [0, False, None]:
            return 'F'
        raise ValueError(f"Invalid RF output value: {value}")

    def _is_empty_frame(self, normalized):
        return all(v == 'F' for v in normalized)

    def process_rf_results(self, results):
        """Process one RF vector and shift the pipeline automatically."""
        if len(results) != 4:
            raise ValueError("RF vector must contain exactly 4 values")

        normalized = [self._normalize_value(v) for v in results]

        if not self.started and self._is_empty_frame(normalized):
            self.history.append(self.get_pipeline_view())
            return False

        self.started = True
        exiting = self.slots[-1]
        self.slots = [
            {'name': self._next_name(), 'status': None},
            self.slots[0],
            self.slots[1],
            self.slots[2],
        ]

        if exiting:
            self.last_exit = self._exit_status(exiting)
        else:
            self.last_exit = None

        for idx, value in enumerate(normalized):
            ball = self.slots[idx]
            if ball is None:
                continue
            if value == 'F':
                ball['status'] = 'F'
            elif value == 'P' and ball['status'] != 'F':
                ball['status'] = 'P'

        self.history.append(self.get_pipeline_view())
        return True

    def _exit_status(self, ball):
        if ball['status'] == 'F':
            return 'FAIL'
        if ball['status'] == 'P':
            return 'PASS'
        return 'PENDING'

    def get_pipeline_view(self):
        view = []
        for ball in self.slots:
            if ball is None:
                view.append('N')
            elif ball['status'] is None:
                view.append(ball['name'])
            else:
                view.append(f"{ball['name']}({ball['status']})")
        return ' '.join(view)

    def get_last_exit(self):
        return self.last_exit or 'None'

    def reset(self):
        self.slots = [None, None, None, None]
        self.history = []
        self.last_exit = None
        self.next_name = 1
        self.started = False

    def print_history(self):
        print("History:")
        for idx, state in enumerate(self.history, start=1):
            print(f"  Step {idx}: {state}")


if __name__ == "__main__":
    pipeline = GolfBallPipeline()

    print("=== Golf Ball Pipeline ===")
    print("Send one RF vector per step, using 4 values:")
    print("  1 = good, X or 0 = bad/empty")
    print("Initial frames may be empty and appear as [F F F F].")
    print("Each step automatically inserts the next ball 1, 2, 3, ...")
    print("Commands: show, history, reset, quit\n")

    while True:
        command = input("RF vector or command: ").strip()
        if not command:
            continue

        lowered = command.lower()
        if lowered == 'quit':
            break
        if lowered == 'show':
            print(f"Pipeline: {pipeline.get_pipeline_view()}")
            print(f"Last exit: {pipeline.get_last_exit()}\n")
            continue
        if lowered == 'history':
            pipeline.print_history()
            print()
            continue
        if lowered == 'reset':
            pipeline.reset()
            print("Pipeline reset.\n")
            continue

        parts = command.split()
        if len(parts) != 4:
            print("Invalid input. Enter 4 values or a command (show, history, reset, quit).\n")
            continue

        try:
            added = pipeline.process_rf_results(parts)
            if not added:
                print("Empty initial frame received; no ball added.")
            print(f"Pipeline: {pipeline.get_pipeline_view()}")
            print(f"Last exit: {pipeline.get_last_exit()}\n")
        except ValueError as e:
            print(f"Error: {e}\n")
