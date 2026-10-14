# 거르기 표 검토 — 사용자 승인용(리스크 심사 재설계 M3, D-33·D-34·D-35)

> 2026-10-14 · 초안 판 — 메커니즘 → 영역 `mech-owners.v1.json`(HWAXRisk 가지 `m3`) · 변경 → 메커니즘·부품 역할 → 영역 `change-routing.v1.json`(가지 `m3-cells`). 둘 다 `review_status: "draft"` 다.

## 이 표가 하는 일

'관련 없는 셀 거르기'(D-33)의 **코드 신호**다. 단위의 변경 → 그 변경이 일으킬 수 있는 메커니즘(표 2) → 그 메커니즘을 보는 영역(표 1) 으로 이어, 어떤 영역에도 닿지 않는 전문가 셀만 '코드로 무관' 이 된다. 그 셀도 그 전문가의 훑기 판단이 함께 '무관' 이라야 거른다(둘 다 무관일 때만). 영역 1순위 대표는 어느 경우든 거르지 않는다.

- **두 표가 다 `approved` 가 되기 전에는 거르기가 꺼져 있다** — 코드 신호가 모든 영역에 '모름' 을 낸다.
- **표가 넓을수록 누락은 적고 호출은 덜 준다.** 좁힐수록 그 반대다(좁혀서 빠진 영역은 훑기 판단 하나로 걸러질 수 있다).

## 지금 초안의 모양 — 한눈에

변경 코드 97개가 각 영역에 닿는 수다(높을수록 그 영역은 거의 걸러지지 않는다).

| xd | sim | cam | rel | soc | disp | mech | pcb | rf | passive | pwr | sh | mem | std | material |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 77 | 74 | 78 | 73 | 11 | 79 | 83 | 72 | 38 | 21 | 47 | 14 | 6 | 11 | 53 |

- `drop_stress`(낙하 응력)가 변경 코드 97개 가운데 61개에 걸리고, 그 메커니즘의 소유·관련이 영역 일곱(sim·mech·rel·disp·cam·xd·pcb)이다. 그래서 그 일곱은 거의 모든 변경에서 '관련 있음' 이다.
- 지금 초안대로면 코드 신호가 '무관' 을 내는 영역은 거의 **mem · soc · std · sh · passive** 다. 거르기가 줄이는 호출은 주로 이 다섯 영역 몫이다.
- xd(122명)는 메커니즘 52개 가운데 24개(소유 11 · 관련 13)에 있다 — xd 셀이 전 셀의 약 3분의 1 이라, xd 를 좁히는 것이 호출을 가장 크게 줄인다.

## 고르실 것

1. **이대로 승인** — 누락 위험이 가장 적다. 거르기는 다섯 영역에서만 준다(호출 어림은 8,000~10,000 의 높은 쪽).
2. **`drop_stress` 의 관련 영역을 좁혀 승인** — 예: 낙하 응력의 관련을 sim·mech·rel·disp 로(cam·xd·pcb 를 뺀다). 그 셋의 셀이 낙하 응력만으로는 '관련' 이 되지 않는다.
3. **xd 를 조립·외관·공차·체결 메커니즘에만 남겨 승인** — xd 의 1순위 대표는 여전히 전 단위를 본다.
4. **고칠 칸을 직접 알려 주기** — 아래 표에서 행·칸을 말해 주시면 고쳐 다시 보여 드린다.

승인은 두 파일의 `review_status` 를 `approved` 로 바꾸는 커밋 하나다(`reviewed_by`·`reviewed_at` 와 함께). 그 뒤 새로 만드는 검토 잡부터 거르기가 켜진다(잡마다 승인 상태를 얼린다 — #40).

## 표 1 — 메커니즘 → 영역(52행)

'소유' 는 그 메커니즘을 아무도 안 봤을 때 누구에게 묻나, '관련' 은 그 영역 사람이 그 메커니즘을 말해도 믿나다. 거르기는 소유 ∪ 관련을 '관련 있음' 으로 읽는다. 전문은 [reference/m3-synthesis.md 3.4](reference/m3-synthesis.md) 에 있다(바꾼 칸에 ✱ 와 로스터 근거).

## 표 2 — 변경 → 메커니즘(같은 메커니즘 목록끼리 묶음)

`mech.`·`if.`·`th.`·`mat.`·`proc.` 는 메커니즘 대분류 줄임이다. '닿는 영역' 은 표 1 을 거친 결과다.

```text
- part.added, node.added
    → mech.mass, if.interference, if.clearance, if.tied, if.tolerance_stackup, mech.drop_stress, mech.rattle
    → 닿는 영역 11: xd sim cam rel disp mech pcb rf pwr sh material | 안 닿음: soc passive mem std
- part.removed, node.removed
    → mech.mass, if.clearance, if.tied_loss, if.tolerance_stackup, mech.drop_stress, mech.rattle
    → 닿는 영역 11: xd sim cam rel disp mech pcb rf pwr sh material | 안 닿음: soc passive mem std
- part.replaced, node.replaced
    → mech.mass, if.interference, if.clearance, if.tied, if.tolerance_stackup, mech.drop_stress, mech.rattle, if.tied_loss, mat.property_uncertain, mat.supplier_change
    → 닿는 영역 13: xd sim cam rel disp mech pcb rf passive pwr sh std material | 안 닿음: soc mem
- part.split, node.split
    → if.tied, if.tied_loss, if.adhesive_area, if.tolerance_stackup, mech.drop_stress, mech.rattle
    → 닿는 영역 9: xd sim cam rel disp mech pcb sh material | 안 닿음: soc rf passive pwr mem std
- part.merged, node.merged
    → if.tied, if.tolerance_stackup, mech.drop_stress, mech.mass, proc.warpage
    → 닿는 영역 9: xd sim cam rel disp mech pcb pwr material | 안 닿음: soc rf passive sh mem std
- part.tree_moved, node.moved_in_tree, edge.hier.added, edge.hier.removed, edge.hier.kind_changed
    → if.tolerance_stackup, proc.tolerance
    → 닿는 영역 5: xd cam rel disp mech | 안 닿음: sim soc pcb rf passive pwr sh mem std material
- part.resized, param.bbox_def_dims, param.bbox_world_dims, param.volume, param.area
    → mech.bending, mech.drop_stress, mech.mass, if.clearance_close, if.interference, if.tolerance_stackup, proc.warpage
    → 닿는 영역 11: xd sim cam rel disp mech pcb rf passive pwr material | 안 닿음: soc sh mem std
- part.thickness_changed, param.min_dim
    → mech.bending, mech.drop_stress, mech.buckling, mech.mass, if.clearance_close, proc.warpage, th.thermal_resistance
    → 닿는 영역 13: xd sim cam rel soc disp mech pcb rf passive pwr std material | 안 닿음: sh mem
- part.moved, part.rotated, param.centroid_world
    → if.clearance, if.clearance_close, if.interference, if.tolerance_stackup, mech.drop_stress
    → 닿는 영역 9: xd sim cam rel disp mech pcb rf pwr | 안 닿음: soc passive sh mem std material
- part.material_changed, param.material.*
    → mat.property_uncertain, mat.supplier_change, th.cte_mismatch, mech.drop_stress, mech.mass, mat.creep, mat.moisture, mat.corrosion, rf.efficiency
    → 닿는 영역 12: xd sim cam rel disp mech pcb rf passive pwr std material | 안 닿음: soc sh mem
- iface.added, edge.iface.added
    → if.touching, if.tied, if.clearance, if.interference, if.tolerance_stackup, mech.drop_stress
    → 닿는 영역 10: xd sim cam rel disp mech pcb rf pwr material | 안 닿음: soc passive sh mem std
- iface.removed, iface.rank_down, edge.iface.removed
    → if.tied_loss, if.clearance, mech.rattle, mech.drop_stress
    → 닿는 영역 11: xd sim cam rel disp mech pcb rf pwr sh material | 안 닿음: soc passive mem std
- iface.clearance_appeared
    → if.clearance, if.clearance_close, if.tied_loss, mech.rattle
    → 닿는 영역 9: xd cam rel disp mech rf pwr sh material | 안 닿음: sim soc pcb passive mem std
- iface.clearance_cleared
    → if.clearance, if.touching, if.interference
    → 닿는 영역 7: xd cam disp mech pcb rf pwr | 안 닿음: sim rel soc passive sh mem std material
- iface.rank_up
    → if.touching, if.tied, if.clearance_close, mech.press_fit, mech.drop_stress
    → 닿는 영역 10: xd sim cam rel disp mech pcb rf pwr material | 안 닿음: soc passive sh mem std
- iface.interference_new
    → if.interference, mech.press_fit, if.tolerance_stackup, mech.drop_stress
    → 닿는 영역 8: xd sim cam rel disp mech pcb material | 안 닿음: soc rf passive pwr sh mem std
- iface.interference_cleared
    → if.interference, if.clearance_close
    → 닿는 영역 7: xd cam disp mech pcb rf pwr | 안 닿음: sim rel soc passive sh mem std material
- iface.gap_changed, param.min_gap
    → if.clearance, if.clearance_close, if.tolerance_stackup, mech.drop_stress, mech.rattle
    → 닿는 영역 10: xd sim cam rel disp mech pcb rf pwr sh | 안 닿음: soc passive mem std material
- iface.band_area_changed, param.contact_area_est, param.band_width
    → if.adhesive_area, if.touching, if.tied, th.thermal_resistance
    → 닿는 영역 10: xd sim cam rel soc disp mech pwr std material | 안 닿음: pcb rf passive sh mem
- iface.penetration_changed, param.penetration_depth, param.penetration_volume
    → if.interference, mech.press_fit
    → 닿는 영역 6: xd cam disp mech pcb material | 안 닿음: sim rel soc rf passive pwr sh mem std
- contact.added, contact.type_changed, edge.contact.added, edge.contact.kind_changed
    → if.touching, if.tied, mech.drop_stress
    → 닿는 영역 8: xd sim cam rel disp mech pcb material | 안 닿음: soc rf passive pwr sh mem std
- contact.removed, edge.contact.removed
    → if.tied_loss, mech.drop_stress
    → 닿는 영역 8: xd sim cam rel disp mech pcb material | 안 닿음: soc rf passive pwr sh mem std
- contact.friction_changed, contact.scope_changed, scope.changed, param.fs
    → if.touching, mech.drop_stress
    → 닿는 영역 7: xd sim cam rel disp mech pcb | 안 닿음: soc rf passive pwr sh mem std material
- mesh.density_changed, edge.iface.status_changed, edge.contact.status_changed, edge.hier.status_changed, edge.bridge.status_changed, edge.load_path.status_changed, edge.net.status_changed, param.n_elems
    → [] (설계 변경 아님)
    → 닿는 영역 0:  | 안 닿음: xd sim cam rel soc disp mech pcb rf passive pwr sh mem std material
- result.part_metric_shift, loadpath.edge_added, loadpath.edge_removed, loadpath.work_shift, edge.load_path.added, edge.load_path.removed, edge.load_path.kind_changed, param.worst_stress, param.worst_g, param.worst_disp, param.min_safety_factor
    → mech.drop_stress
    → 닿는 영역 7: xd sim cam rel disp mech pcb | 안 닿음: soc rf passive pwr sh mem std material
- dim.named_changed, dim.named_unmeasured, param.dim
    → mech.bending, mech.drop_stress, if.clearance, if.clearance_close, if.tolerance_stackup, proc.warpage
    → 닿는 영역 11: xd sim cam rel disp mech pcb rf passive pwr material | 안 닿음: soc sh mem std
- asm.rollup_changed, param.rollup
    → if.tied, if.touching, if.tolerance_stackup, mech.mass
    → 닿는 영역 7: xd sim cam disp mech pwr material | 안 닿음: rel soc pcb rf passive sh mem std
- cross.bridge_stale
    → if.cross_file_untrusted, mech.drop_stress
    → 닿는 영역 7: xd sim cam rel disp mech pcb | 안 닿음: soc rf passive pwr sh mem std material
- ecad.net_changed
    → el.net, el.si_pi, el.emi
    → 닿는 영역 8: rel soc mech pcb rf passive pwr mem | 안 닿음: xd sim cam disp sh std material
- ecad.component_moved
    → el.si_pi, el.emi, proc.solder, th.hotspot, th.solder_fatigue, mech.bending
    → 닿는 영역 12: sim cam rel soc disp mech pcb rf passive pwr mem std | 안 닿음: xd sh material
- ecad.stackup_changed
    → el.si_pi, proc.warpage, th.thermal_resistance, mech.bending
    → 닿는 영역 11: sim rel soc disp mech pcb passive pwr mem std material | 안 닿음: xd cam rf sh
- edge.iface.kind_changed
    → if.touching, if.tied, if.interference, if.clearance, if.tied_loss, mech.drop_stress
    → 닿는 영역 10: xd sim cam rel disp mech pcb rf pwr material | 안 닿음: soc passive sh mem std
- edge.bridge.added, edge.bridge.removed, edge.bridge.kind_changed
    → if.cross_file_untrusted
    → 닿는 영역 2: sim mech | 안 닿음: xd cam rel soc disp pcb rf passive pwr sh mem std material
- edge.net.added, edge.net.removed, edge.net.kind_changed
    → el.net, el.si_pi
    → 닿는 영역 6: soc pcb rf passive pwr mem | 안 닿음: xd sim cam rel disp mech sh std material
- param.material.E
    → mat.property_uncertain, mech.drop_stress, mech.bending, mech.buckling
    → 닿는 영역 9: xd sim cam rel disp mech pcb passive material | 안 닿음: soc rf pwr sh mem std
- param.material.rho
    → mat.property_uncertain, mech.mass, mech.drop_stress
    → 닿는 영역 9: xd sim cam rel disp mech pcb pwr material | 안 닿음: soc rf passive sh mem std
- param.material.sigy
    → mat.property_uncertain, mech.drop_stress, mech.fatigue
    → 닿는 영역 8: xd sim cam rel disp mech pcb material | 안 닿음: soc rf passive pwr sh mem std
- param.material.nu
    → mat.property_uncertain, mech.drop_stress
    → 닿는 영역 8: xd sim cam rel disp mech pcb material | 안 닿음: soc rf passive pwr sh mem std
- param.material.mid, param.material.keyword, param.material.match_basis
    → mat.property_uncertain
    → 닿는 영역 2: sim material | 안 닿음: xd cam rel soc disp mech pcb rf passive pwr sh mem std

```

## 표 3 — 변경 종류 대체와 부품 역할 → 영역

변경 종류 대체는 단위 줄에 종류 칸이 있을 때만 쓴다(저장된 단위 줄에는 없다 — 표 2 가 코드만으로 다 푼다). 부품 역할은 영역을 **더하기만** 한다(무관으로 만들지 않는다).

```text
== change_kinds ==
- dimension: mech.bending, mech.drop_stress, mech.mass, if.clearance_close, if.interference, if.tolerance_stackup, proc.warpage
- placement: if.clearance, if.clearance_close, if.interference, if.tolerance_stackup, mech.drop_stress
- topology: if.touching, if.tied, if.interference, if.clearance, if.tied_loss, mech.drop_stress
- material: mat.property_uncertain, mat.supplier_change, th.cte_mismatch, mech.drop_stress, mech.mass, mat.creep, mat.moisture, mat.corrosion, rf.efficiency
- type: mech.mass, if.interference, if.clearance, if.tied, if.tolerance_stackup, mech.drop_stress, mech.rattle, if.tied_loss, mat.property_uncertain, mat.supplier_change
- count: mech.mass, if.interference, if.clearance, if.tied, if.tolerance_stackup, mech.drop_stress, mech.rattle, if.tied_loss
- discretization: []
- result: mech.drop_stress
- load_path: mech.drop_stress
- consistency: null(모름)
- electrical: el.net, el.si_pi, el.emi
- contact_type: if.touching, if.tied, mech.drop_stress
- parameter: if.touching, mech.drop_stress
- none: null(모름)

== roles ==
- pcb: pcb passive soc mem
- battery: pwr
- display: disp
- shield_can: rf pcb rel
- fpcb: pcb
- housing: mech xd
- frame: mech xd
- bracket: mech xd
- screw: mech xd
- tape: mech material

```
