import numpy as np
from skimage.metrics import structural_similarity as ssim
from scipy.spatial import KDTree


class TileFitterSciKit:
    def __init__(self, tiles_data, match_res=5, penalty=0.02):
        # tiles_data here is the 'small_tiles' list from TileProcessor
        self.penalty = penalty
        self.usages = [0.0 for x in range(len(tiles_data))]
        self.tiles_data = tiles_data
        self.match_res = match_res
        self.winners = np.array([], dtype=float)

        print("Initializing KDTree for hybrid search...")
        # 1. Convert tiles to NumPy arrays once
        # We reshape them from flat lists back into (5x5x3) blocks for SSIM
        self.tiles_np = [
            np.array(t).reshape((self.match_res, self.match_res, 3))
            for t in tiles_data
        ]

        # 2. Pre-calculate average colors for the Tree
        avg_colors = [t.mean(axis=(0, 1)) for t in self.tiles_np]
        self.tree = KDTree(np.array(avg_colors))
        print("KDTree + SSIM Hybrid Fitter Ready.")

    def fit_tiles(self, work_queue, result_queue):
        EOQ_VALUE = None  # Sentinel
        while True:
            try:
                img_data, img_coords = work_queue.get(True)
                if img_data == EOQ_VALUE:
                    break
                tile_index = self.get_best_fit_tile(img_data)
                result_queue.put((img_coords, tile_index))
            except KeyboardInterrupt:
                pass

        self.get_winning_stats()  # print stats
        # Signal that this worker is done
        result_queue.put((EOQ_VALUE, EOQ_VALUE))

    def get_best_fit_tile(self, img_data):
        """
        img_data: A flat list of pixels (from original code's getdata())
        We convert it to NumPy to use the Tree and SSIM.
        """
        # Convert the incoming list to a 5x5x3 array
        target_np = np.array(img_data).reshape(
            (self.match_res, self.match_res, 3))

        # Step 1: KDTree Pruning (The "Bucket" step)
        target_avg = target_np.mean(axis=(0, 1))
        _, indices = self.tree.query(target_avg, k=100)

        best_raw_score = float('-inf')
        best_score = -1
        best_fit_tile_index = indices[0]

        # Step 2: SSIM Refinement
        for idx in indices:
            candidate_np = self.tiles_np[idx]

            # SSIM needs to know the range of pixel values (0-255)
            try:
                score = ssim(target_np,
                             candidate_np,
                             channel_axis=2,
                             data_range=255,
                             win_size=self.match_res-2)
                score = score - self.usages[idx]

            except ValueError as e:
                # codes sometimes breaks and hangs.
                print(f'Got exception {e} \
                        skipping index{idx} \
                        data was {type(candidate_np)}')
                continue

            if score > best_score:
                best_score = score
                best_fit_tile_index = idx
                best_raw_score = score

            # Early exit if we find an amazing match
            if score > 0.98:
                best_raw_score = score
                break

        self.winners = np.append(self.winners, best_raw_score)
        self.usages[best_fit_tile_index] = \
            self.usages[best_fit_tile_index] + self.penalty
        return best_fit_tile_index

    def get_winning_stats(self):
        """Prints statistical analysis of the tile match quality."""
        if self.winners.size == 0:
            print("No winners recorded yet.")
            return

        print("\n--- Tile Match Quality Stats ---")
        print(f"Total Blocks Matched: {len(self.winners)}")
        print(f"Mean SSIM:    {np.mean(self.winners):.4f}")
        print(f"Median SSIM:  {np.median(self.winners):.4f}")
        print(f"Highest SSIM: {np.max(self.winners):.4f} (Best Match)")
        print(f"Lowest SSIM:  {np.min(self.winners):.4f} (Worst Match)")
        print("--------------------------------\n")
