

import json
import math
import random
import csv
import time
import os

# 1. UTILITY: Euclidean's distance

def euclidean(p1, p2):
    """Return straight-line distance between two [x, y] points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


# 2. JSON PARSING

def load_data(filepath="data.json"):
    """Read and parse the input JSON file. Returns dict with warehouses, agents, packages."""
    with open(filepath, "r") as f:
        data = json.load(f)

    # Basic validation
    assert "warehouses" in data, "Missing 'warehouses' key"
    assert "agents" in data,     "Missing 'agents' key"
    assert "packages" in data,   "Missing 'packages' key"

    print(f"[✔] Loaded {len(data['packages'])} packages, "
          f"{len(data['agents'])} agents, "
          f"{len(data['warehouses'])} warehouses.")
    return data



# 3. AGENT-PACKAGE ASSIGNMENT

def assign_packages(packages, agents, warehouses):                      
    assignment = {agent_id: [] for agent_id in agents}

    for pkg in packages:
        wh_pos   = warehouses[pkg["warehouse"]]   # warehouse coordinates
        best_agent = None
        best_dist  = float("inf")

        for agent_id, agent_pos in agents.items():
            dist = euclidean(agent_pos, wh_pos)
            if dist < best_dist:
                best_dist  = dist
                best_agent = agent_id

        assignment[best_agent].append(pkg)
        print(f"  Package {pkg['id']} (at {pkg['warehouse']}) → Agent {best_agent} "
              f"(dist={best_dist:.2f})")

    return assignment



# 4. DELIVERY SIMULATION

def simulate_deliveries(assignment, agents, warehouses,use_delays=True, delay_range=(0.5, 2.0)):
   
    results = {}

    for agent_id, pkgs in assignment.items():
        current_pos   = list(agents[agent_id])  #starting position of agent
        total_dist    = 0.0
        delivered     = []
        log           = []                        

        print(f"\n[Agent {agent_id}] Starting at {current_pos}, "
              f"{len(pkgs)} package(s) assigned.")

        for pkg in pkgs:
            wh_pos   = warehouses[pkg["warehouse"]]
            dest_pos = pkg["destination"]

            # Leg 1: agent travels from current position to warehouse
            leg1 = euclidean(current_pos, wh_pos)
            # Leg 2: warehouse → destination
            leg2 = euclidean(wh_pos, dest_pos)

            trip_dist = leg1 + leg2
            total_dist += trip_dist

            # BONUS: random delay simulation
            delay = 0.0
            if use_delays:
                delay = round(random.uniform(*delay_range), 2)

            log.append({
                "package"        : pkg["id"],
                "warehouse"      : pkg["warehouse"],
                "destination"    : dest_pos,
                "leg1_to_wh"    : round(leg1, 4),
                "leg2_to_dest"  : round(leg2, 4),
                "trip_distance" : round(trip_dist, 4),
                "delay_min"     : delay
            })

            print(f"  → Pick up {pkg['id']} from {pkg['warehouse']} {wh_pos}: "
                  f"{leg1:.2f} units  |  Deliver to {dest_pos}: {leg2:.2f} units"
                  + (f"  [delay: {delay} min]" if use_delays else ""))

            delivered.append(pkg["id"])
            current_pos = dest_pos    # agent stays at last destination

        # Efficiency = average distance per package (lower = better)
        n = len(delivered)
        efficiency = round(total_dist / n, 4) if n > 0 else 0.0

        results[agent_id] = {
            "packages_delivered": n,
            "total_distance"    : round(total_dist, 4),
            "efficiency"        : efficiency,
            "packages"          : delivered,
            "log"               : log
        }

        print(f"  [{agent_id}] Total distance: {total_dist:.4f}  "
              f"Efficiency: {efficiency:.4f}")

    return results


# 5. REPORT GENERATION

def generate_report(results):
    """
    Build the final report dict.
    Best agent = lowest efficiency score (least distance per package).
    """
    # Only consider agents that delivered at least one package
    active = {aid: v for aid, v in results.items() if v["packages_delivered"] > 0}

    best_agent = min(active, key=lambda aid: active[aid]["efficiency"]) if active else None

    report = {}
    for agent_id, data in results.items():
        report[agent_id] = {
            "packages_delivered": data["packages_delivered"],
            "total_distance"    : data["total_distance"],
            "efficiency"        : data["efficiency"]
        }

    report["best_agent"] = best_agent
    return report


# 6. SAVE JSON REPORT

def save_report(report, filepath="report.json"):
    """Serialize and write the report to a JSON file."""
    with open(filepath, "w") as f:
        json.dump(report, f, indent=4)
    print(f"\n[✔] Report saved → {filepath}")

#Optional
# 1.BONUS A: ASCII MAP VISUALIZER

def ascii_map(warehouses, agents, packages, assignment, grid_size=20, scale=6):
    """
    Render a scaled-down ASCII grid showing:
      W = Warehouse  A = Agent  * = Package destination
    Routes are shown as dotted lines on the grid.
    """
    cols = grid_size + 1
    rows = grid_size + 1
    grid = [["·" for _ in range(cols)] for _ in range(rows)]

    def plot(pos, char):
        """Scale real coordinates to grid coordinates and mark the cell."""
        gx = min(int(pos[0] / scale), grid_size)
        gy = min(int(pos[1] / scale), grid_size)
        # Invert Y so top-left is (0,0) on screen
        grid[grid_size - gy][gx] = char

    def draw_line(p1, p2, char="-"):
        """Bresenham-style line between two scaled points."""
        x0, y0 = min(int(p1[0] / scale), grid_size), min(int(p1[1] / scale), grid_size)
        x1, y1 = min(int(p2[0] / scale), grid_size), min(int(p2[1] / scale), grid_size)
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            if grid[grid_size - y0][x0] == "·":
                grid[grid_size - y0][x0] = char
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0  += sx
            if e2 < dx:
                err += dx
                y0  += sy

    # Draw routes first (so labels overwrite lines)
    for agent_id, pkgs in assignment.items():
        agent_pos = agents[agent_id]
        cur = agent_pos
        for pkg in pkgs:
            wh_pos   = warehouses[pkg["warehouse"]]
            dest_pos = pkg["destination"]
            draw_line(cur, wh_pos,   "~")
            draw_line(wh_pos, dest_pos, "~")
            cur = dest_pos

    # Plot destinations
    for pkg in packages:
        plot(pkg["destination"], "*")

    # Plot warehouses
    for wid, pos in warehouses.items():
        plot(pos, wid[0])   # "W"

    # Plot agents
    for aid, pos in agents.items():
        plot(pos, aid[0])   # "A"

    print("\n" + "═" * 50)
    print("  FastBox Route Map  (scale: 1 cell = {} units)".format(scale))
    print("═" * 50)
    # Y-axis labels
    for i, row in enumerate(grid):
        y_label = (grid_size - i) * scale
        print(f"{y_label:>3} │ {'  '.join(row)}")
    # X-axis
    print("    └" + "──" * (cols) )
    x_labels = "     " + "  ".join(
        str(c * scale).rjust(2) for c in range(0, cols, 2)
    )
    print(x_labels[:80])
    print("\n  Legend:  W=Warehouse  A=Agent  *=Destination  ~=Route  ·=Empty\n")



# 2.BONUS B: EXPORT TOP PERFORMER TO CSV

def export_top_performer_csv(results, report, filepath="top_performer.csv"):
    """Write the best agent's delivery log to a CSV file."""
    best = report.get("best_agent")
    if not best:
        print("[!] No best agent to export.")
        return

    log = results[best]["log"]
    fieldnames = ["package", "warehouse", "destination",
                  "leg1_to_wh", "leg2_to_dest", "trip_distance", "delay_min"]

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(log)

    print(f"[✔] Top performer ({best}) exported → {filepath}")

#3. BONUS C: NEW AGENT JOINING MID-DAY

def add_mid_day_agent(agents, new_agent_id, position, unassigned_packages,
                      warehouses, results):
    """
    Simulate a new agent joining mid-day and handling any remaining packages.
    Appends their results into the existing results dict.
    """
    if not unassigned_packages:
        print(f"\n[Mid-Day] No unassigned packages for new agent {new_agent_id}.")
        return results

    print(f"\n[Mid-Day] Agent {new_agent_id} joined at {position} "
          f"and will handle {len(unassigned_packages)} package(s).")

    agents[new_agent_id] = position
    new_assignment = {new_agent_id: unassigned_packages}
    new_results = simulate_deliveries(new_assignment, agents, warehouses, use_delays=False)
    results.update(new_results)
    return results



# MAIN ENTRY POINT

def main():
    print("=" * 55)
    print("    FastBox Logistics Simulator")
    print("=" * 55)

    # Step 1: Load data 
    data       = load_data("data.json")
    warehouses = data["warehouses"]
    agents     = data["agents"]
    packages   = data["packages"]

    #Step 2: Assign packages to nearest agents 
    print("\n[2] Assigning packages to nearest agents...")
    assignment = assign_packages(packages, agents, warehouses)

    # BONUS C: Mid-day agent joining 
    # (Uncomment the block below to activate)
    # mid_day_packages = []  # move some packages here to reassign
    # results = add_mid_day_agent(
    #     agents, "A4", [50, 50], mid_day_packages, warehouses, {}
    # )

    #BONUS A: ASCII Map
    ascii_map(warehouses, agents, packages, assignment)

    # ── Step 3: Simulate deliveries 
    print("\n[3] Simulating deliveries...")
    results = simulate_deliveries(assignment, agents, warehouses, use_delays=True)

    # ── Step 4: Generate & display report 
    print("\n[4] Generating report...")
    report = generate_report(results)

    print("\n" + "─" * 40)
    print("  FINAL REPORT")
    print("─" * 40)
    for agent_id, stats in report.items():
        if agent_id == "best_agent":
            continue
        print(f"  {agent_id}: {stats['packages_delivered']} pkg(s) | "
              f"dist={stats['total_distance']:.2f} | "
              f"efficiency={stats['efficiency']:.2f}")
    print(f"\n Best Agent: {report['best_agent']}")
    print("─" * 40)

    # Verify all packages accounted for
    delivered_count = sum(
        v["packages_delivered"] for k, v in report.items() if k != "best_agent"
    )
    print(f"\n  ✔ Total packages delivered: {delivered_count} / {len(packages)}")

    # ── Step 5: Save report 
    save_report(report)

    # ── BONUS B: Export top performer CSV 
    export_top_performer_csv(results, report)

    print("\n[Done] Simulation complete.\n")


if __name__ == "__main__":
    main()