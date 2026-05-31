import math


# =========================================================
# ORBIT MATH CORE
# =========================================================

def circular_orbit_period(mu, r):
    return 2 * math.pi * math.sqrt(r**3 / mu)


def circular_velocity(mu, r):
    return math.sqrt(mu / r)


def semi_major_axis_from_period(mu, T):
    return (mu * (T / (2 * math.pi))**2) ** (1 / 3)


def vis_viva(mu, r, a):
    return math.sqrt(mu * (2 / r - 1 / a))


def orbit_is_safe(rp, ra, min_r, max_r):
    return rp >= min_r and ra <= max_r


# =========================================================
# SCORING (MISSION STYLE BIAS)
# =========================================================

def score_solution(dv, time, style):
    if style == "fuel":
        return dv
    elif style == "time":
        return time
    elif style == "auto":
        return dv + 0.05 * time
    return dv


# =========================================================
# MAIN SOLVER
# =========================================================

def find_best_phasing_orbit(
    mu,
    orbit_radius,
    phase_angle,
    min_radius,
    max_radius,
    style="fuel",
    max_phasing_orbits=100,
    max_delta_v=-1,
):
    phase_angle %= 2 * math.pi

    T = circular_orbit_period(mu, orbit_radius)
    v_circ = circular_velocity(mu, orbit_radius)
    fraction = phase_angle / (2 * math.pi)

    best = None
    rejected = []

    N_limit = max_phasing_orbits if max_phasing_orbits > 0 else 10_000

    for N in range(1, N_limit + 1):

        # =================================================
        # LOWER PERIAPSIS OPTION
        # =================================================
        T_fast = T * (1 - fraction / N)

        if T_fast > 0:
            a = semi_major_axis_from_period(mu, T_fast)

            rp = 2 * a - orbit_radius
            ra = orbit_radius

            if orbit_is_safe(rp, ra, min_radius, max_radius):

                v = vis_viva(mu, orbit_radius, a)
                dv = 2 * abs(v - v_circ)

                if max_delta_v < 0 or dv <= max_delta_v:

                    score = score_solution(dv, T_fast * N, style)

                    candidate = {
                        "method": "lower periapsis",
                        "phasing_orbits": N,
                        "delta_v": dv,
                        "score": score,
                        "periapsis": rp,
                        "apoapsis": ra,
                        "phasing_period": T_fast,
                        "total_time": T_fast * N,
                    }

                    if best is None or score < best["score"]:
                        best = candidate
                else:
                    rejected.append(("lower", N, "Δv limit"))

        # =================================================
        # RAISE APOAPSIS OPTION
        # =================================================
        T_slow = T * (1 + (1 - fraction) / N)

        a = semi_major_axis_from_period(mu, T_slow)

        rp = orbit_radius
        ra = 2 * a - orbit_radius

        if orbit_is_safe(rp, ra, min_radius, max_radius):

            v = vis_viva(mu, orbit_radius, a)
            dv = 2 * abs(v - v_circ)

            if max_delta_v < 0 or dv <= max_delta_v:

                score = score_solution(dv, T_slow * N, style)

                candidate = {
                    "method": "raise apoapsis",
                    "phasing_orbits": N,
                    "delta_v": dv,
                    "score": score,
                    "periapsis": rp,
                    "apoapsis": ra,
                    "phasing_period": T_slow,
                    "total_time": T_slow * N,
                }

                if best is None or score < best["score"]:
                    best = candidate
            else:
                rejected.append(("raise", N, "Δv limit"))
        else:
            rejected.append(("raise", N, "orbit unsafe"))

    # =========================================================
    # FULL RETURN BUNDLE (CLEAN INTERFACE)
    # =========================================================
    return {
        "best": best,
        "inputs": {
            "mu": mu,
            "orbit_radius": orbit_radius,
            "phase_angle": phase_angle,
            "min_radius": min_radius,
            "max_radius": max_radius,
            "style": style,
            "max_phasing_orbits": max_phasing_orbits,
            "max_delta_v": max_delta_v,
        },
        "stats": {
            "searched_orbits": N_limit,
            "rejected_count": len(rejected),
        },
    }


# =========================================================
# OUTPUT LAYER (PURE DISPLAY)
# =========================================================

def print_solution(bundle, body_radius):
    sol = bundle["best"]
    inp = bundle["inputs"]

    if sol is None:
        print("No valid phasing solution found.")
        return

    angle_deg = math.degrees(inp["phase_angle"])
    direction = "ahead of you" if inp["phase_angle"] <= math.pi else "behind you"

    print("\n=== PHASING MANEUVER REPORT ===\n")

    print("Mission Input Summary")
    print("---------------------")
    print(f"Orbit altitude:     {(inp['orbit_radius'] - body_radius)/1000:.1f} km")
    print(f"Target angle:       {angle_deg:.2f}° ({direction})")
    print(f"Optimization style: {inp['style']}")
    print(f"Δv limit:           {inp['max_delta_v'] if inp['max_delta_v'] > 0 else 'unlimited'}")
    print(f"Orbit limit:        {inp['max_phasing_orbits'] if inp['max_phasing_orbits'] > 0 else 'unlimited'}")

    print("\nBest Maneuver")
    print("-------------")
    print(f"Method:         {sol['method']}")
    print(f"Phasing orbits: {sol['phasing_orbits']}")
    print(f"Total Δv:       {sol['delta_v']:.2f} m/s")
    print(f"Score:          {sol['score']:.2f}")

    print("\nOrbit Targets")
    print("-------------")
    print(f"Periapsis:      {(sol['periapsis'] - body_radius)/1000:.1f} km")
    print(f"Apoapsis:       {(sol['apoapsis'] - body_radius)/1000:.1f} km")
    print(f"Phasing period: {sol['phasing_period']:.1f} s")
    print(f"Total time:     {sol['total_time']:.1f} s")

    print("\nInstructions")
    print("------------")
    if sol["method"] == "lower periapsis":
        print("1. Burn retrograde to lower periapsis")
    else:
        print("1. Burn prograde to raise apoapsis")

    print(f"2. Coast for {sol['phasing_orbits']} orbit(s)")
    print("3. Circularize at rendezvous")

if __name__ == "__main__":

    KERBIN_RADIUS = 600_000
    KERBIN_MU = 3.5316e12
    KERBIN_SOI = 84_159_286

    result = find_best_phasing_orbit(
        mu=KERBIN_MU,
        orbit_radius=700_000,
        phase_angle=math.radians(75),
        min_radius=KERBIN_RADIUS + 70_000 + 10_000,
        max_radius=KERBIN_SOI - 50_000,
        style="auto",
        max_phasing_orbits=10,
        max_delta_v=200,
    )

    print_solution(result, KERBIN_RADIUS)

    
