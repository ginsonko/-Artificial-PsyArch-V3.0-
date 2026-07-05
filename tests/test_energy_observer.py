from __future__ import annotations

from apv3test.runtime import APV3EnergyItem, APV3EnergyObserver


def test_state_debt_keeps_unresolved_residual_costly() -> None:
    observer = APV3EnergyObserver()
    quiet = observer.observe([APV3EnergyItem(sa_label="quiet")])
    unresolved = observer.observe([APV3EnergyItem(sa_label="surprise", epistemic_debt=0.8)])

    assert unresolved.pressure_loss == quiet.pressure_loss
    assert unresolved.state_debt > quiet.state_debt


def test_action_free_energy_rewards_expected_information_gain() -> None:
    observer = APV3EnergyObserver()
    no_probe = observer.observe([APV3EnergyItem(sa_label="surprise", real_energy=1.0)])
    probe = observer.observe([
        APV3EnergyItem(sa_label="surprise", real_energy=1.0, expected_information_gain=0.8)
    ])

    assert probe.pressure_loss == no_probe.pressure_loss
    assert probe.action_free_energy < no_probe.action_free_energy


def test_lambda_fast_uses_additive_logit_not_product_veto() -> None:
    observer = APV3EnergyObserver()

    strong_grasp = observer.lambda_fast(grasp=3.0, habit=0.0, demand_slow=0.0)
    weak_grasp = observer.lambda_fast(grasp=0.0, habit=0.0, demand_slow=0.0)

    assert strong_grasp > weak_grasp
    assert strong_grasp > 0.9


def test_tau_focus_tightens_on_surprise_and_widens_on_ambiguity() -> None:
    observer = APV3EnergyObserver()

    baseline = observer.tau_focus(candidate_entropy=0.0, surprise_pressure=0.0)
    surprised = observer.tau_focus(candidate_entropy=0.0, surprise_pressure=2.0)
    ambiguous = observer.tau_focus(candidate_entropy=2.0, surprise_pressure=0.0)

    assert surprised < baseline
    assert ambiguous > baseline

