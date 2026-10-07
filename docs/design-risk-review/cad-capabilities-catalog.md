# 심사용 ECAD·MCAD 능력 카탈로그 (전체)

> 2026-10-07 생성. 요약·결론은 [cad-capabilities.md](cad-capabilities.md) 에 있다. 이 문서는 그 근거가 되는 능력 178건 전체다.
> 만든 방법: 심사 엔진 소비처·좌석 계약·StepForge 141도구·ODB 리포·해석 어댑터를 읽고(병렬 7), 도메인 묶음 8개에서 리스크 질문 → 필요한 능력 행 495개를
> 뽑아 행마다 반박 검증한 뒤(수정 215 · 탈락 30), 세 렌즈 비평(추가 제안 74 · 이의 51)을 소스로 다시 확인해 합쳤다.
> 상태는 **2026-10-07 dev 게이트웨이 실호출** 기준이다 — cae00 의 odb-hub(문서상 27도구)는 dev 에서 확인할 수 없어 `unverified` 로 적었다.

| 상태 | 뜻 |
|---|---|
| 있음 | 게이트웨이 도구가 값을 내고 심사 스냅샷도 싣는다 — 리비전 비교·인용이 된다 |
| 도구는 있음 · 스냅샷 미수집 | 게이트웨이 도구는 값을 내지만 심사 어댑터가 싣지 않는다 — 좌석이 직접 불러야 하고 리비전 비교가 안 된다 |
| 부분 | 있지만 칸·정밀도가 모자라다 |
| 리포에 있음 · 미노출 | 소유 리포가 이미 파싱·계산하지만 게이트웨이 도구가 없다 |
| 계약에만 | 심사 ECAD 계약 4도구에 이름만 있다 |
| 없음 | 어디에도 없다 |

우선순위 — **P0** 없으면 그 도메인 좌석이 핵심 메커니즘을 경험칙으로만 말한다 · **P1** 정성 우려를 수치·위치로 좁힌다 · **P2** 있으면 좋다.

## MCAD 쪽(StepForge) — 63건

상태 분포 — 부분 26 · 도구는 있음 · 스냅샷 미수집 24 · 없음 11 · 있음 2. 우선순위 — P0 32 · P1 30 · P2 1.

### 식별·리비전

#### MCAD-01 · 파트 역할·분류 식별과 역할 온톨로지 확장

**부분 · P0**

- 돌려줘야 하는 것 — 인스턴스 경로(path)마다 role(온톨로지 키 또는 사람이 준 문자열)·role_source(사람|이름|분류)·role_confidence{name, shape, neighbor}·category·form·tags[]·expected_neighbors[]·missing_neighbors[], 판 단위 by_role{역할→개수}. 더해야 할 역할 낱말 — 디스플레이 층(cover_window·utg·oca·polarizer·panel·support_plate), hinge, 실링재(gasket·seal_tape 를 구조 접착·완충 폼과 분리), 도전성 가스켓·접점 스프링, magnet, coil·ferrite, 방열 부품(vapor_chamber·graphite_sheet·heat_pipe), fpcb·cable, speaker·receiver·mic·lra·mesh, sensor, key·switch, deco·lens_window, pcm·tab, stiffener
- 지금 — find_parts(role=, tag=)·describe_part(identity)·describe_assembly(by_category) — 좌석 열림. identify_part·identify_parts — 좌석 닫힘. set_part_metadata(role=, tags=)로 사람이 온톨로지 밖 이름도 지정한다(쓰기, 그 값이 정본). REST GET /find-parts·/identify-parts
- 빠진 것 — 역할이 16종뿐이다 — 디스플레이 계열은 glass 하나, FPCB 는 pcb 동의어, CLIP 은 fastener 동의어, 가스켓·폼·테이프는 cushion_adhesive 한 역할. 자동 식별은 이름 동의어에 기댄다. 어댑터가 role·tags 를 읽지 않아 rr_ir 에 없다. 역할을 실어도 씨앗 fastener_dense·adhesive_dependent 가 이름 정규식 코드 경로라 소비처 전환이 함께 필요하다. 고칠 자리는 셋 — 온톨로지 확장(StepForge), 사람 지정(사이드카·set_part_metadata), 어댑터 수집
- 풀리는 도메인(10) — mech · xd · disp · cam · sh · material · pcb · soc · pwr · rf
- 메커니즘 — interface.adhesive_area · interface.tied · material.adhesive_aging · electrical.emi · thermal.thermal_resistance · new:electrical.antenna_detune · new:mechanical.fold_crease_strain
- 질문 예 — 어느 파트가 커버윈도우·UTG·OCA·편광판·패널·쿠션·서포트 플레이트·힌지인가 / 어느 파트가 방사체이고 어느 파트가 차폐·접지 금속인가 / 접착(PSA·폼테이프)으로만 붙은 계면은 어느 쌍인가
- 선행 — MCAD-12
- 근거 — SF/core/data/part_ontology.yaml(roles 16키 — yaml 로 직접 셈) · GW describe_part(001a0dcc02ce36213eacd49, SHIELD_CAN_A) identity.role·role_source·expected_neighbors · GW set_part_metadata 스키마 · HR/adapters/mcad.py:625-655(role·tags 없음) · HR/state.py:647-660 · HR/assets/character-seed-rules.v1.json(dsl null·pattern) · SF/app/rest.py:999-1013

#### MCAD-02 · 리비전을 넘는 인스턴스 대응표·인스턴스 키

**부분 · P0**

- 돌려줘야 하는 것 — pairs[]{path_a, path_b, how[pid|invariants|elimination|position|name], confidence 0~1}, ambiguous[], only_a[], only_b[], frame_fit{rotation_deg, translation_mm[3], fit_scale, residual_mm, rms_all_mm, used_anchors}, partial(bool)·unexamined[개]. 새로 필요한 칸 — 리비전 불변 instance_key·key_basis(occurrence_id|anchored_position|path)
- 지금 — match_parts_across(동기)·run_job(kind='match')(쓰기 잡) — 근거 순서 pid → 불변량 → 위치(닻 프레임) → 이름. 좌석 닫힘. compare_revisions(좌석 열림)는 경로가 같다는 전제. 심사 pair 사다리는 exact_path → geom_fp → fuzzy
- 빠진 것 — 소스에 리비전 불변 인스턴스 id 가 없다 — 경로는 이름을 이은 것이고 동명 형제는 #순번, 실물 NX 판은 같은 이름 134자리를 __2 접미사 파일로 싣는다. 심사는 match_parts_across 를 쓰지 않고 자체 fuzzy 에 위치 항이 없으며 합동 파트는 geom_fp 가 같다. ckey 가 이름·형상 버킷·재질이라 같은 이름 인스턴스가 한 주체로 접힌다 — 자리가 리스크를 정하는 부품을 가르려면 주체 키에 인스턴스 구분자가 필요하다
- 풀리는 도메인(12) — xd · mech · disp · cam · sh · rf · pwr · pcb · soc · material · sim · rel
- 메커니즘 — interface.cross_file_untrusted · interface.clearance_close · new:process.data_comparability
- 질문 예 — DV1 의 이 파트는 DV2 의 어느 파트인가 — 파일 이름과 내보내기 순번이 바뀌어도 답이 같은가 / 같은 형상이 수십 자리에 놓인 캐패시터 중 코너 자리 것은 어느 것인가
- 선행 — MCAD-04 · MCAD-08
- 근거 — GW match_parts_across 스키마·독스트링 · disc match_parts_across 42칸 · SF/core/loader.py:107,474 · SF/docs/NX_EXPORT_GUIDE.md:20-21,35,244 · HR/sameas.py grep(centroid|bbox_world|world) 0건 · HR/ir_builder.py:208-230,259-261 · DB rr_ir_nodes(PLATE_1·2·3 geom_fp 5e9e41f79bc04709 동일)·rr_diff_events 0행

#### MCAD-03 · 실장 부품 바디의 지정번호·품번·사내 속성과 BOM 행

**도구는 있음 · 스냅샷 미수집 · P1**

- 돌려줘야 하는 것 — 인스턴스별 identity.designator(이름에서 뽑은 회로 지정번호)·part_number·meta/extras(VP.PCB_SIDE 등)·tags. 정의별 BOM rows[]{name, step_file, count, volume_each[mm³], material, density, density_source, mass_total}. 없는 칸 — 공급처
- 지금 — describe_part.identity(좌석 열림) · identify_part·bom_export(좌석 닫힘) · 사이드카 part_number·extras · compare_revisions 의 renamed·material_changed(좌석 열림)
- 빠진 것 — 어댑터가 designator·part_number·tags·meta 를 읽지 않는다. 실물 이름은 '<지정번호>_<품번>' 이고 같은 이름이 134자리라 이 키로는 품번 수준 대응까지만 된다 — 그래서 P1 로 두고 인스턴스 구분은 MCAD-02 가 P0 로 진다. 라이브 픽스처 값은 null
- 풀리는 도메인(5) — xd · pcb · pwr · soc · passive
- 메커니즘 — interface.clearance · material.supplier_change
- 질문 예 — PCB 실장 부품 상면과 쉴드캔 내면 사이 간극이 좁은 그 바디는 어느 품번인가 / 형상은 같은데 품번이 바뀐 파트는 무엇인가
- 선행 — MCAD-02 · JOIN: refdes↔MCAD 인스턴스 대응
- 근거 — GW describe_part(…, SHIELD_CAN_A) identity.designator·part_number null · disc identify_part 32칸·bom_export 24칸 · HR/adapters/mcad.py grep(designator|part_number|tags) 0건 · SF/docs/NX_EXPORT_GUIDE.md:20-21,244 · SF/docs/SIDECAR_SPEC.md:84,90

#### MCAD-04 · 자세·척도 불변 형상 기술자

**부분 · P1**

- 돌려줘야 하는 것 — 정의마다 norm{volume/d³, OBB 세 변/d ×3, 주관성모멘트/d² ×3}(무차원, d 는 정의 형상의 축정렬 대각선), scale_mm[mm], world.centroid[mm×3], keys{geo_key, tol_key}, 부피 없는 정의는 norm=null + reason. 새로 필요한 칸 — 방향 맞춘 상자(OBB) 세 변[mm] 스칼라, OBB 대각선 정규화
- 지금 — snapshot_descriptors(좌석 닫힘, REST GET) · find_similar_parts(좌석 열림) · duplicate_shapes · slenderness_check.extents{min, mid, max}. 심사 geom_fp 는 sorted(round(size_def, 2))·부피·면적
- 빠진 것 — 비평 제안(have_not_ingested·P0)을 partial·P1 로 고쳤다. norm 은 '어셈블리를 옮기거나 돌려도' 불변일 뿐 정의가 자기 좌표계 안에서 비스듬히 저장된 것끼리는 못 견준다(독스트링 실측 상대차 0.104~0.987) — NX 반입 규약이 바디를 절대좌표로 굽기 때문에 바로 그 경우다. 수집해도 geom_fp 와 같은 한계를 물려받는다. geom_fp 는 세 변을 정렬해 좌표축 90° 회전에는 이미 불변이고 깨지는 것은 비스듬한 배치뿐이다(실물 빈도 unverified)
- 풀리는 도메인(3) — xd · mech · pcb
- 메커니즘 — process.tolerance · new:process.data_comparability
- 질문 예 — 이 파트의 치수가 정말 바뀌었나, 같은 부품이 다른 각도로 놓였을 뿐인가
- 근거 — GW snapshot_descriptors 독스트링 · disc snapshot_descriptors.norm 한계 · GW compare_dimension() not_yet('외곽 치수(방향 맞춘 상자 세 변)') · HR/ir_builder.py:208-230 · SF/docs/NX_EXPORT_GUIDE.md:105-111 · HR/diff.py:1373-1391

#### MCAD-05 · 출처·세대·사람 개입·엔진 빌드 스탬프

**부분 · P0**

- 돌려줘야 하는 것 — build{sha, at, source}, geo_key, files[]{relpath, sha256, unit, header{originating_system, time_stamp}}, sidecar{found, applied, of, unmatched}, human_edits{renamed, part_metadata, interface_verdicts, joint_verdicts, placements_adjusted, excluded_from_deck}[건], last_jobs.{parse, detect, graph}{job_id, status, finished_at}, yardstick{are_default, sets[벌]}, caveats[]{code, count, of}. 없는 칸 — change_stamp(소스 내부 함수뿐), revision_label·predecessor_project_id
- 지금 — REST tree.json 의 files[].sha256·header_unit 은 수집(REST 채널). model_provenance·step_header_info(좌석 닫힘, REST GET) · heaxstep_forge_system_capabilities(build) · snapshot_descriptors.keys · list_unknowns(좌석 열림)
- 빠진 것 — 어댑터는 버전을 heaxstep_forge_system_status 로만 읽는데 그 응답은 version '0.1.0' 뿐이라 엔진 세대를 못 가른다(라이브 diff 의 app_version_parity 는 null). MCP 폴백 스냅샷의 source_hash 는 빈 입력으로 만든 상수라 3건이 같다. 사이드카 적용 수·사람 수정 건수·원본 CAD·detect 잡 id 는 미수집. 과제끼리 잇는 리비전 계보 칸이 StepForge 에 없다
- 풀리는 도메인(3) — xd · mech · sim
- 메커니즘 — interface.cross_file_untrusted · new:process.data_comparability
- 질문 예 — 두 스냅샷의 수치 차이는 설계가 바뀐 것인가, 재는 엔진이 바뀐 것인가 / 이 스냅샷 뒤에 사람이 고쳤거나 다시 검출했는가
- 근거 — GW heaxstep_forge_system_capabilities(build.sha cb0c578…) · DB rr_snapshots.app_versions_json(version 0.1.0·extra null 4/4)·source_ids_json(hash ef83b18d… 3건)·rr_diffs.comparability_json · HR/adapters/base.py:293-319 · GW list_unknowns caveats detected_on_other_build 16 · disc model_provenance 100칸 · SF/app/db.py:20-24 · SF/docs/SIDECAR_SPEC.md:238 · SF/core/geokey.py:55

### 어셈블리·좌표

#### MCAD-06 · 어셈블리 트리·파트 기본 형상 속성 동결

**있음 · P0**

- 돌려줘야 하는 것 — 노드(file|assembly|part)의 canon_key(과제명 뗀 경로)·부모, part attrs — bbox_def[6]·size_def[3]·size_sorted[3][mm], bbox_world[6]·centroid_world[3][mm 월드], volume[mm³], area[mm²], min_dim[mm](bbox 최소 변 — 벽 두께 아님), instance_count, solid_count, status_flags, part_of 엣지
- 지금 — REST GET /tree(정본)·/parts → rr_ir 노드 → rr_diff part.added·removed·resized·moved·thickness_changed. 좌석은 list_parts(world_bbox·world_center)·describe_part·project_tree
- 빠진 것 — REST 채널에서만 온전하다 — MCP 폴백은 world 계열을 버린다(MCAD-58). 옛 파싱분은 volume·area·centroid 가 null(스냅샷 4/4 — backfill·재파싱은 사람 몫). min_dim 은 평판에서만 두께다(MCAD-34). 어느 파트가 보드·셀인지는 이름으로 고른다(MCAD-01)
- 풀리는 도메인(6) — xd · mech · pwr · pcb · material · rf
- 메커니즘 — mechanical.mass · interface.clearance_close · process.warpage
- 질문 예 — 셀 외형(두께·폭·길이)이 리비전 간 얼마나 바뀌었고 위치가 이동했나 / 보드 외곽 치수와 두께는 얼마인가
- 근거 — HR/adapters/mcad.py:625-655, 784-794 · GW list_parts(…) world_bbox·world_center · DB rr_ir_nodes part 12행(size_sorted·min_dim 12/12, bbox_world 3/12, volume·area·centroid_world 0/12)·rr_snapshots.missing_json

#### MCAD-07 · 단위·좌표계 검문 입력(G4·G6·R-004·R-005)

**부분 · P0**

- 돌려줘야 하는 것 — unit_system, files[].header_unit·schema_ap, warnings[]{code(unit_mismatch|suspect_coordinate_systems|files_all_overlap…), severity, ref, count}, 선언 단위 분포(units.declared·odd_files), 파일 쌍 file_pairs[]{file_a, file_b, min_gap[mm], bound_confirmed}, assembly_check(로컬 좌표 판 판정)
- 지금 — REST tree.json 의 unit_system·files·warnings 수집(REST 채널). get_project_meta.unit_system(좌석 열림) · summarize_warnings·step_header_info·model_provenance.units·file_distances·assembly_check(좌석 닫힘, REST GET)
- 빠진 것 — 입력이 REST tree.json 전용이다. MCP 폴백이면 G4 null·G6 차단이라 diff·타깃이 만들어지지 않는다 — 라이브 스냅샷 4건 중 3건이 blocked=1. 같은 사실을 주는 도구가 이미 있는데 어댑터가 부르지 않는다(get_project_meta 한 호출이 unit_system 을 준다). 차단 게이트라 전 도메인에 걸린다
- 풀리는 도메인(15) — xd · sim · cam · rel · soc · disp · mech · pcb · rf · passive · pwr · sh · mem · std · material
- 메커니즘 — interface.cross_file_untrusted · new:process.data_comparability
- 질문 예 — REST 를 못 읽은 캡처에서도 단위·좌표계·파일 배치를 검문할 수 있는가 / 다중 STEP 파일이 같은 전역 좌표계로 내보내졌는가
- 선행 — MCAD-58
- 근거 — HR/state.py:212, 246-290 · HR/adapters/mcad.py:445, 535-538 · DB rr_states(blocked 3/4 — G4 warnings_unavailable, G6 unit_unknown) · GW get_project_meta(…) unit_system mm · disc summarize_warnings 24칸·file_distances 16칸 · SF/app/rest.py:661-684, 1288, 1685, 1816

#### MCAD-08 · 제품 좌표계 선언·승계와 리비전 간 프레임 패리티

**부분 · P0**

- 돌려줘야 하는 것 — yardstick.frame{same(true|false|unknown), solved, rotation_deg, translation[mm×3], scale, used_pairs, outliers, rms_all[mm]}, identity_shift_mm[mm], product_frame{origin[mm×3], axes 3×3, basis(model_pca|product_box), sign_rule, signs_determined, extents_mm[3]}. 새로 필요한 칸 — basis=declared(사람이 선언하고 다음 리비전이 승계)
- 지금 — compare_snapshots(yardstick 의 frame 축·identity_shift_mm, 좌석 열림) · align_frames·where_is·part_location(좌석 닫힘). 심사 coordinate_ok 는 각 스냅샷의 G4 만 본다
- 빠진 것 — 심사 comparability 에 리비전 간 프레임 패리티 키가 없다 — 다른 원점으로 내보낸 리비전은 전 파트가 part.moved 로 선다. StepForge 의 제품 프레임은 선언값이 아니라 파트 분포에서 유도해 파트가 더해지면 움직이고 대칭 판은 부호를 못 가른다. 선언·승계 자리는 어디에도 없다
- 풀리는 도메인(5) — xd · mech · rel · sim · soc
- 메커니즘 — interface.cross_file_untrusted · mechanical.drop_stress · new:process.data_comparability
- 질문 예 — 두 리비전이 같은 좌표계로 저장됐는가 / 전 파트가 이동으로 뜬 것은 조립이 옮겨진 것인가 좌표계가 달라진 것인가
- 선행 — MCAD-02
- 근거 — HR/diff.py:209-300(coordinate_ok 는 G4, 프레임 키 없음), 1381-1391 · SF/core/frame.py:1-40 · disc compare_snapshots(frame·identity_shift_mm)·align_frames 24칸·where_is(order_determined)

#### MCAD-09 · 제품 구역·층·정규화 위치

**도구는 있음 · 스냅샷 미수집 · P1**

- 돌려줘야 하는 것 — 파트별 zone(corner_x0y0…|edge_x0…|center)·zone_uv[0~1]·zone_margin, where_is{layer(몇째 층), normalized[0~1×3], octant, frame_coords_mm[3]}, order_determined, zone_unavailable
- 지금 — part_location(REST POST)·where_is(REST GET) — 좌석 닫힘. 월드 중심·상자는 스냅샷(REST 채널)과 list_parts·describe_part(좌석 열림)에 있다
- 빠진 것 — 구역·층은 미수집이다. 행들의 상태가 갈렸으나(have_not_ingested 대 partial) 월드 좌표는 MCAD-06 이 지므로 이 항목은 구역·층만 본다. 프레임이 리비전 사이에서 같다는 보장이 없어(MCAD-08) 구역 이름을 그대로 diff 하면 프레임 흔들림이 설계 변경으로 나온다. 정사각·대칭 판에서는 구역이 안 나온다
- 풀리는 도메인(4) — xd · soc · sh · rel
- 메커니즘 — mechanical.drop_stress · mechanical.vibration
- 질문 예 — 변경이 제품의 어느 구역(코너·에지·중앙)·어느 층에 몰려 있나 / AP·음향 모듈이 제품의 어느 구역에 있는가
- 선행 — MCAD-08
- 근거 — disc part_location 43칸·where_is 41칸 · SF/app/rest.py:1037, 2235 · HR/adapters/base.py:88-114(GET 전용) · HR/adapters/mcad.py:17-19

#### MCAD-10 · 낙하 방향별 사전 지표·첫 접지 파트

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — rows[]{direction, contact(면|선|점), contact_area_mm2, moment_arm_mm, effective_mass_ratio, rotational_share, ground{parts[], next[]{behind_mm}}}, by_ground_part, load_paths(graph 잡 필요), impact_speed_mm_s, ok(시트 바디가 섞이면 false)
- 지금 — drop_check(height_mm 는 사람 입력)·structure_report·risk_screen 의 corner_drop_concentration — 전부 좌석 닫힘
- 빠진 것 — 어댑터 미수집·좌석 닫힘·REST POST. 균일 밀도 가정이고 가속도·응력은 내지 않는다. 방향 이름과 첫 접지 파트는 제품 프레임이 리비전 사이에서 같아야 비교된다(MCAD-08) — 선언 프레임의 축으로 고정하지 않으면 diff 가 프레임 흔들림을 설계 변경으로 낸다. dev 에 해석 리포트가 0건이라 이 형상 지표의 비중이 크다(행 검증 인용)
- 풀리는 도메인(6) — mech · rel · sim · disp · cam · soc
- 메커니즘 — mechanical.drop_stress
- 질문 예 — 낙하 26방향 중 어느 방향에서 무엇이 먼저 닿고 그 접지에서 글래스·PCB 까지 하중 경로가 몇 겹인가 / 코너·후면 낙하에서 윈도우가 먼저 닿는가 프레임 립이 먼저 닿는가
- 선행 — MCAD-08 · MCAD-19 · MCAD-51
- 근거 — disc drop_check 54칸 · SF/app/rest.py:1076(POST) · SF/core/data/failure_modes.yaml(corner_drop_concentration) · AS:2061-2105

#### MCAD-11 · 자세(펼침·접힘·착용)별 형상 묶음

**부분 · P1**

- 돌려줘야 하는 것 — pose_id(open|closed|각도[deg]|worn), 같은 리비전의 자세별 과제 묶음, 자세 쌍의 moved[]{distance_mm, rotated_deg}·gap_changed[], 자세별 계면 표·화면 간 간극 분포[mm]
- 지금 — 자세별 STEP 을 과제 둘로 올리면 compare_snapshots(좌석 열림)·what_changed_near 로 견줄 수 있고 apply_dimension 으로 같은 치수를 두 자세에서 잴 수 있다
- 빠진 것 — '같은 리비전·다른 자세' 묶음이 StepForge(판 하나 = 과제 하나)에도 심사 봉투(kind 당 소스 1건)에도 없다. 규격 없이 넣으면 두 자세가 다른 리비전처럼 diff 되어 전 파트 이동으로 뜬다. 폴더블 과제에서는 사실상 P0 다
- 풀리는 도메인(4) — disp · mech · xd · rf
- 메커니즘 — interface.clearance_close · new:mechanical.fold_crease_strain · new:electrical.antenna_detune
- 질문 예 — 접은 상태에서 화면끼리·힌지 하우징·FPCB 가 어디서 닿고 얼마나 남는가 / 자세마다 방사체–금속 간 거리가 얼마나 달라지는가
- 선행 — MCAD-02 · MCAD-56
- 근거 — GW list_tool_apps(heax-step_forge)에 compare_snapshots·apply_dimension · HR/adapters/mcad.py:324-329 · PLAN:684('한 스냅샷에 kind 당 최대 1건')

#### MCAD-12 · 실물 어셈블리 반입 상태(분리 솔리드·사이드카·모듈 봉투)

**부분 · P0**

- 돌려줘야 하는 것 — 층·모듈 단위로 분리된 솔리드(디스플레이 층, 카메라 모듈 외곽 봉투, 팩 외곽·PCM·탭, 실장 부품 바디), 사이드카 parts[]{material, role, part_number, shell.thickness[mm], extras}, 접힌/펼친 상태 표기. 확인값 — describe_assembly.parts, list_unknowns.caveats(no_material·no_structure 의 count/of)
- 지금 — 싣는 틀은 있다 — import_archive·intake·upload_step, 사이드카 규격, set_part_metadata, NX 반출 지침
- 빠진 것 — 도구가 아니라 데이터의 문제다. dev 과제는 전부 픽스처이고(행 검증 인용 — 73건) 심사 스냅샷 4건은 3파트 적층 픽스처 하나에서 떴다. 대부분의 MCAD 능력이 전제하는 '층이 솔리드로 분리돼 있고 이름·재질이 실려 있다' 가 실물에서 확인된 적이 없다. 모듈 내부 사실(OIS 가동부·팩 내부·화각)은 공급사 소유라 외형도·사양서(side other)로 받고 CAD 에는 '봉투 대 주변 간극' 만 남긴다. cae00 실물 과제 유무는 unverified
- 풀리는 도메인(8) — disp · cam · pwr · mech · xd · sh · rf · soc
- 메커니즘 — material.property_uncertain · interface.cross_file_untrusted
- 질문 예 — 심사에 올릴 어셈블리에 디스플레이 층과 카메라 모듈이 분리된 솔리드로 들어 있고 재질·시트 두께가 딸려 오는가 / 팩 내부(셀·탭·PCM)가 별도 파트로 분해돼 있는가
- 선행 — OTHER: 모듈 외형도·사양서
- 근거 — DB rr_snapshots 4건(stepforge_project_id 001a02ba21cd51064a68c35, part 노드 스냅샷당 3) · GW list_unknowns(001a0dcc02ce36213eacd49) no_material 12/12·no_structure · SF/docs/SIDECAR_SPEC.md:84-104 · SF/docs/NX_EXPORT_GUIDE.md:14-22

#### MCAD-13 · 외장(노출) 파트·면 분류

**없음 · P1**

- 돌려줘야 하는 것 — 파트별 exposed(bool)·exposed_area[mm²]·exposed_ratio[0~1], 외곽 면 구분(front|back|side|corner), 재질·표면처리 연결 키
- 지금 — 간접 지표만 — where_is.layer, drop_check.ground.parts, build_cavity 의 hull
- 빠진 것 — 노출 여부 칸이 도구·온톨로지 어디에도 없다. 비평 제안은 partial 이었으나 대용 지표만 있고 능력 자체는 없어 missing 으로 둔다. 밀폐 안팎 라벨(MCAD-47)과 다른 축이다
- 풀리는 도메인(5) — xd · rel · soc · rf · material
- 메커니즘 — material.corrosion · mechanical.drop_stress · new:electrical.sar
- 질문 예 — 어느 파트·면이 바깥에 드러나 손에 닿는가 / 송신 방사체에서 인체가 닿는 외표면까지 거리는 얼마인가
- 선행 — MCAD-08 · MCAD-53
- 근거 — SF/core/partid.py·ontology.py·frame.py grep(exposed|외장) 0건 · SF/core/data/part_ontology.yaml(역할 16종) · disc where_is·drop_check

### 계면·조인트

#### MCAD-14 · 계면 표 동결(쌍·종류·수치)

**있음 · P0**

- 돌려줘야 하는 것 — 쌍마다 kind(tied|touching|clearance|interference), min_gap[mm], contact_area_est[mm², 접촉 면적이 아니라 공차 밴드 면적], band_width[mm, 면 짝 폭의 최댓값], penetration_depth[mm, 하한], penetration_volume[mm³], status(auto|manual|confirmed), cross_file, note. 이벤트 edge kind_changed(rank up/down)
- 지금 — list_interfaces(좌석 열림·패널 지정 도구)·interface_graph·describe_interface → REST /interfaces(정본) → rr_ir iface 엣지 → rr_diff
- 빠진 것 — have 는 '쌍의 존재·kind·여덟 수치가 동결돼 [e:] 로 인용된다' 까지다. 수치 변화 이벤트는 tol_config_hash null 로 전부 빠지고(MCAD-16), 안 잰 쌍·추정 kind 표시가 IR 에 없으며(MCAD-15), clearance_gap(기본 0.5 mm) 밖 쌍은 행이 없고(MCAD-25), 쌍 대응은 파트 대응이 선 뒤에만 성립한다(MCAD-02). band_width 변화에는 의미 이벤트가 없고 고리 모양 접촉에서는 비드 폭이 아니다. 전부 status=auto 다
- 풀리는 도메인(11) — mech · xd · disp · cam · sh · soc · rel · pwr · rf · pcb · material
- 메커니즘 — interface.tied · interface.touching · interface.clearance · interface.interference · interface.tied_loss · interface.adhesive_area
- 질문 예 — base→target 에서 kind 가 내려가거나 간섭으로 올라간 계면 쌍은 어느 것인가 / 패널·카메라 모듈과 프레임·브래킷 사이 경계 계면의 kind 와 min_gap 은 얼마인가
- 선행 — MCAD-16 · MCAD-15 · MCAD-02
- 근거 — HR/adapters/mcad.py:797-848 · DB rr_ir_edges(tied 8·part_of 16, attrs 11키, tol_config_hash null 8/8)·rr_iface_ledger 0행 · HR/diff.py:40-41 · GW list_interfaces(…) counts tied 12·clearance 3·interference 1 · HR/planner.py:255-275

#### MCAD-15 · 계면 행의 신뢰·방식·관통 세부 칸과 경로 끝점

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — 행별 path_a·path_b(유일 키), partial(bool — 참이면 kind 는 추정), gap_method(raw|shell_half_t|shell_t), pen_method(boolean|screen|''), penetration_thickness[mm, 2V/A], contained_fraction[0~1], pen_over_min_extent[0~1], sliver_verdict. 목록 단위 unmeasured[쌍], geometry_sets[벌], relations_total·truncated·omitted
- 지금 — list_interfaces·describe_interface·describe_part.contacts·inspect_report(좌석 열림). REST /interfaces 는 MCP 와 같은 함수를 부르므로 어댑터가 이미 받는 응답에 이 칸들이 있다
- 빠진 것 — 엣지 attrs 매핑에 penetration_depth·volume 둘뿐이라 diff·[e:] 에 못 들어온다. '간섭 0' 과 '못 쟀다' 가 같은 모양으로 동결되고, 슬리버·억지끼움·모델 겹침과 시트 바디 두께 미보정을 가를 근거가 스냅샷에 없다. MCP 폴백은 끝점을 이름 유일성에 기대 동명이면 엣지를 뺀다 — 소스는 path_a·path_b 를 준다. 행들의 P1 을 P0 로 올렸다(미측정 표시는 간섭·tied 소실 근거의 진위 문제다). 고칠 자리는 어댑터 매핑 한 곳
- 풀리는 도메인(8) — mech · xd · disp · material · pcb · soc · rf · pwr
- 메커니즘 — interface.interference · mechanical.press_fit · interface.tied_loss · electrical.emi · material.creep
- 질문 예 — 간섭 쌍이 스친 것(슬리버)인가 파고든 것인가 — 파고든 두께와 비율은 / 이 계면 행은 끝까지 잰 값인가 추정인가 / 쉴드캔이 떠 보이는 것이 설계인가 시트 바디 두께 미보정인가
- 근거 — GW list_interfaces(…, limit=2) 행 22칸·unmeasured·geometry_sets · DB rr_snapshot_calls REST /interfaces 응답 행(partial·gap_method·pen_method·penetration_thickness·path_a·path_b) · SF/app/rest.py:601-617 · HR/adapters/mcad.py:824-838, 851-861 · HR/assets/rules-seed.v1.json(R-001)

#### MCAD-16 · 검출 잣대(tol_config) 값·해시·행 단위 잣대 키

**부분 · P0**

- 돌려줘야 하는 것 — tolerances{tied_gap[mm], clearance_gap[mm], tied_area[mm²], tied_width[mm], tied_area_ratio, tied_width_ratio, normal_align, face_budget, face_scan_budget, max_face_pairs, penetration_min_volume[mm³], penetration_tol_thickness[mm]}(12키, get_project_meta 는 20키), tolerances_are_default, 과제·행의 tol_key·geo_key, tolerance_sets[]{set, rows, differs_from_default, measured_at}, 행별 detected_at[epoch s]
- 지금 — REST /interfaces 응답의 tolerances 12키(어댑터가 이미 받는다) · get_project_meta.tol_config·tol_is_default · describe_interface.tol_key·geo_key · interface_graph.tolerance_sets(좌석 열림) · StepForge interfaces 표의 params·detected_at 칼럼
- 빠진 것 — 어댑터가 REST /projects 의 project.tol_config(기본 공차면 null)와 detect 잡 params 4키만 읽어 정본 채널에서도 tol_config_hash 가 null 이다(4/4) — G7 tol_parity 가 서지 않아 간극·밴드면적·띠 폭·관통 변화가 전부 제외된다. 이미 받은 /interfaces 의 tolerances 는 버린다. 행 단위 잣대는 벌크 목록에 없다(describe_interface·explain_kind 한 쌍 조회뿐) — 범위 검출은 옛 잣대 행을 남기는데 심사는 과제 단위 해시 하나로 판정한다
- 풀리는 도메인(10) — mech · xd · disp · cam · material · rel · sh · pwr · rf · pcb
- 메커니즘 — interface.tied_loss · interface.clearance_close · interface.adhesive_area · interface.interference
- 질문 예 — 간극·밴드 면적·관통 깊이가 얼마에서 얼마로 바뀌었나 / 두 리비전의 검출 잣대가 같은가
- 근거 — DB rr_snapshot_calls(REST /projects 응답 tol_config=null, REST /interfaces 응답 tolerances 12키)·rr_snapshots.degraded_json(tol_config_unknown 4/4)·rr_diffs(tol_parity null, tol_unknown 6) · HR/adapters/mcad.py:370-384, 608-622 · HR/diff.py:209-220 · GW get_project_meta(…) tol_config 20키 · GW list_interfaces tolerances_note · SF/app/db.py:51-65

#### MCAD-17 · 판정 민감도·수치 내력

**도구는 있음 · 스냅샷 미수집 · P1**

- 돌려줘야 하는 것 — tolerance_sweep{knob, current, flips_at{value, direction, source}, confidence, in_detect_range}, explain_kind{decided_by, margin_rel, would_flip_if, replay.agrees, face_pairs_complete, detected_at}, explain_number{입력·잣대·형상·잡·낡음}, cross_check{두 경로 값·차·정본}
- 지금 — tolerance_sweep(REST POST)·explain_kind·explain_number·cross_check(REST GET) — 좌석 닫힘. check_claim 은 좌석 열림
- 빠진 것 — 어댑터 호출 목록에 없다. tied 가 touching 으로 바뀐 이벤트가 설계 변경인지 잣대 경계의 흔들림인지 가릴 근거가 없다. 쌍마다 형상을 다시 읽으므로 kind 가 바뀐 쌍과 간섭 쌍에만 붙이는 것이 현실적이다(비용 unverified)
- 풀리는 도메인(3) — mech · xd · sim
- 메커니즘 — interface.tied_loss · interface.clearance_close
- 질문 예 — 이 계면 판정이 잣대에 얼마나 매달려 있나 / 인용한 수치는 어느 공차·어느 형상·어느 잡에서 나왔나
- 선행 — MCAD-16
- 근거 — GW list_tool_apps(heax-step_forge)에 넷 다 있음 · disc tolerance_sweep 61칸·explain_kind 75칸 · HR/adapters/mcad.py:17-19 · SF/app/rest.py:892-899, 990, 1103

#### MCAD-18 · 간섭 의도 분류와 탄성 파트 모델링 상태

**부분 · P1**

- 돌려줘야 하는 것 — 쌍별 intent(press_fit|compression|thread_overlap|snap_fit|modeling_overlap|unknown), 근거 칸(양쪽 role, material, penetration_thickness[mm], contained_fraction, sliver_verdict), 확정 status·확정자·시각. 파트별 modeled_state(free|compressed)
- 지금 — 근거 칸은 있다 — 관통 세부·sliver_verdict, 역할, set_interface(kind, note)·confirm_interfaces(쓰기), 엣지 status 는 스냅샷에 실린다
- 빠진 것 — 의도를 담는 정형 칸이 없다(set_interface 인자는 kind·note). 모델링 상태 칸도 어디에도 없다 — 실을 압축 후 형상으로 그렸으면 간섭이 0 이라 눌림량·압축률·TIM 압착·접점 눌림을 읽는 숫자가 뜻을 잃는다. 사람 확정이 0건이라 간섭이 전부 미확정 경고다. 실물에서 의도된 겹침이 몇 건인지는 unverified
- 풀리는 도메인(6) — mech · xd · disp · rf · sh · material
- 메커니즘 — interface.interference · mechanical.press_fit · new:interface.seal_compression
- 질문 예 — 이 간섭은 의도된 압입·압축인가, 모델링 겹침인가, 설계 오류인가 / 이 가스켓은 자유 상태로 모델링됐는가
- 선행 — MCAD-15 · MCAD-01
- 근거 — GW set_interface 스키마(project_id·name_a·name_b·kind·note) · HR/state.py:236-240 · HR/assets/rules-seed.v1.json(R-001) · DB rr_iface_ledger 0행 · SF/docs/SIDECAR_SPEC.md:84-104(읽은 범위에 모델링 상태 칸 없음)

#### MCAD-19 · 조인트·구조 추론(운동 부류·강체 증명·하중 경로)

**도구는 있음 · 스냅샷 미수집 · P1**

- 돌려줘야 하는 것 — joints[]{a, b(경로), motion_class(rigid|revolute|prismatic|cylindrical|planar|spherical|universal|higher_pair|unknown), dof_upper_bound, axis_dir, center[mm], patches[]}, structure_report{proven_rigid_clusters, tied_but_unproven_rigid, mechanism_candidates, bridges, articulation_points, patterns, mirror_groups}. graph 잡이 없으면 null + 사유
- 지금 — list_joints·describe_interface·describe_part.structure·describe_assembly.structure(좌석 열림) · structure_report·assembly_graph(좌석 닫힘) · REST GET /joints·/structure
- 빠진 것 — graph 잡 산출물 전체가 rr_ir 밖이라 diff·[e:] 인용이 안 된다. hinge 역할이 없어 힌지 쌍은 이름에 기댄다. 자유도는 상한이고 작동 중 간섭은 없다(MCAD-23). 라이브 픽스처는 graph 잡이 없어 구조 칸이 null
- 풀리는 도메인(6) — mech · disp · rel · sh · pwr · cam
- 메커니즘 — mechanical.fatigue · mechanical.vibration · mechanical.rattle
- 질문 예 — 힌지 축의 조인트 부류와 축 방향은 무엇이고 패널 접힘선과 일치하는가 / IMU·마이크가 진동원과 같은 강체 묶음에 얹혀 있나
- 선행 — MCAD-14
- 근거 — disc list_joints 24칸·structure_report 51칸 · GW describe_part(…) structure null·structure_note · GW list_unknowns caveats no_structure · HR/adapters/mcad.py:389-391, 495-508 · SF/app/rest.py:700, 737

#### MCAD-20 · 구속 미증명·자유물체·붙잡는 구조

**도구는 있음 · 스냅샷 미수집 · P1**

- 돌려줘야 하는 것 — free_bodies{detail[]{part, path, why}, shell_still_free_detail[]{thickness_mm, nearest_gap_mm, partner, residual_after_t_mm}, sheet_without_thickness}, rigid_body_check{bodies, zero_energy_modes_min, floating_groups, verdict}, what_holds{held_by, partners, joints[], fasteners[], proven_rigid_clusters, free_body}
- 지금 — describe_assembly(connectivity·structure — 좌석 열림, 판 단위 수) · free_bodies·rigid_body_check·what_holds(좌석 닫힘, REST GET)
- 빠진 것 — IR 에는 고아 파트 수만 들어간다. 파트별 사유·유격[mm]·시트 바디 두께 보정 잔차는 닫힌 도구에 있다. '증명 못 함' 은 '움직인다' 가 아니고 체결력·마찰·접착은 형상에 없다
- 풀리는 도메인(6) — mech · sim · rel · cam · sh · pwr
- 메커니즘 — mechanical.rattle · interface.touching · mechanical.vibration
- 질문 예 — 사이드키·SIM 트레이·카메라 데코 중 구속이 증명되지 않은 것은 무엇이고 유격은 몇 mm 인가 / 자유물체·뜬 덩어리가 있는가
- 선행 — MCAD-14 · MCAD-19
- 근거 — HR/adapters/mcad.py:495-508, 875-893 · disc free_bodies 39칸·rigid_body_check 39칸·what_holds 53칸·describe_assembly 62칸 · SF/app/rest.py:885, 1824, 2028

#### MCAD-21 · 체결(스크류·핀·보스) 위치·치수·분포

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — fasteners[]{screw_part, hole_part(경로), axis_point[mm 월드], axis_dir, screw_diameter·hole_diameter[mm, 모델 원통 지름], radial_clearance[mm, 음수는 억지끼움], engagement_depth[mm], connector{members, engagement, head_seat}}, interference_fit[개]. 분포 by_zone[개], nearest{min_mm, median_mm, max_mm}(중심 간 거리), eccentricity{offset_mm, over_half_extent}, detail[].center[mm]. graph 잡이 없으면 0 이 아니라 null
- 지금 — fastener_report(graph 잡 선행)·fastener_distribution(역할과 위치만으로 돈다) — 좌석 닫힘, REST GET. 좌석은 describe_part(structure.fasteners)·describe_interface(coaxial)·find_parts(role='fastener')로 하나씩 간접 조회한다
- 빠진 것 — 어댑터 미수집이라 체결이 [p:]·[e:] 속성으로 없고 심사 쪽 체결 사실은 이름 정규식 씨앗 하나다 — 수집하면 씨앗도 속성을 읽게 바꿔야 한다. 역할을 단언하지 않아 핀·축도 같은 표에 오고 connector.role 은 늘 unknown. nearest 는 중심 간 거리라 볼트와 제 너트가 최근접으로 잡힌다. 토크·예압·전기적 접지 여부는 형상에 없다. 체결 행에 리비전 대응 키가 없어 diff 는 집계만 낸다(MCAD-22)
- 풀리는 도메인(8) — mech · rel · pcb · soc · pwr · sh · rf · cam
- 메커니즘 — process.screw_torque · mechanical.drop_stress · mechanical.bending · mechanical.press_fit · mechanical.rattle
- 질문 예 — PCB·브래킷을 잡는 스크류와 보스는 몇 개이고 어디에 있으며 한쪽에 몰려 있지 않나 / 대형 BGA 코너에서 가장 가까운 보드 고정홀까지 거리는 얼마인가 / 스크류 체결 깊이와 면내 유격은 얼마인가
- 선행 — MCAD-19 · MCAD-01
- 근거 — disc fastener_report 27칸(role 한계)·fastener_distribution 38칸(nearest 한계) · HR/state.py:647-652 · HR/assets/character-seed-rules.v1.json · HR/adapters/mcad.py:17-19 · SF/app/rest.py:974, 1809 · GW compare_dimension() not_yet(체결 행)

#### MCAD-22 · 형상 특징(체결 짝·보스·리브·구멍) 리비전 간 대응 키

**부분 · P1**

- 돌려줘야 하는 것 — feature_key(소유 인스턴스 키 + 종류 + 파트 국소 좌표 양자화 + 축), feature_kind, center_local[mm×3], axis[3], radius_mm, depth_mm. 지금 있는 것 — compare_snapshots 의 connectors_delta·connectors_unmapped_b·clusters_split·clusters_merged
- 지금 — compare_snapshots(좌석 열림)가 동축 커넥터의 추가·삭제를 파트 대응 위에서 센다
- 빠진 것 — 보스·리브·구멍·개구 행에는 리비전 불변 id 가 없어 '보스 하나가 0.8 mm 옮겨졌다' 가 인용 단위가 될 수 없다. 치수 기록부도 체결 행을 받지 않는다. 비평 제안은 missing 이었으나 커넥터 층 비교가 있어 partial 로 둔다
- 풀리는 도메인(4) — mech · sh · rf · pcb
- 메커니즘 — process.screw_torque · mechanical.bending
- 질문 예 — DV1 의 이 보스·구멍·체결 자리가 DV2 에서 어디로 갔나
- 선행 — MCAD-02 · MCAD-21 · MCAD-36
- 근거 — disc compare_snapshots 121칸(connectors_delta·connectors_unmapped_b) · GW compare_dimension() not_yet · disc fastener_report·rib_boss_features 칸표(id 칸 없음)

#### MCAD-23 · 운동 범위 스윕 간섭

**없음 · P1**

- 돌려줘야 하는 것 — joint id, 변수(각도[deg] 또는 변위[mm])의 범위·스텝, 스텝별 min_gap[mm]·상대 파트, 첫 간섭 위치[mm], 간섭 부피[mm³]
- 지금 — list_joints(운동 부류·자유도 상한·축)·저장된 자세의 정적 간극(axis_gap)
- 빠진 것 — 조인트 축을 따라 파트를 움직이며 간극을 훑는 계산이 없다(검색 무결과, core/kinematics.py 는 운동 분류 함수뿐). 가동부가 별도 솔리드로 오는지도 실물 미확인이라 모듈 내부는 봉투 대 주변 간극(MCAD-26)으로 대신한다
- 풀리는 도메인(4) — mech · xd · cam · disp
- 메커니즘 — interface.interference · interface.clearance_close · mechanical.rattle
- 질문 예 — 힌지·SIM 트레이·키가 움직이는 전 구간에서 무엇과 부딪히는가 / OIS·AF 가동부와 데코 하면 사이 간극이 스트로크보다 큰가
- 선행 — MCAD-19 · OTHER: 스트로크·회전 범위 사양
- 근거 — GW search_tools('운동 범위 스윕 간섭 힌지 회전 각도별 최소 간극 motion sweep interference') 해당 도구 없음 · SF/core/kinematics.py(def 목록) · SF core·app grep(swept|insert_dir|disassembl) 형상 기능 0건

#### MCAD-24 · 해석 덱 연결(메시 계보·접촉 미리보기·메시 요약)

**부분 · P1**

- 돌려줘야 하는 것 — part_mesh_map.parts[]{step_file, source_name, worked_name, pid, kind, status, node_count, elem_count}, mesh_report{parts[]{part, pid, kind, thickness(셸), quality}, failures, substitutions, artifacts.kfile}, contact_preview{contacts[]{path_a, path_b, kind, type, options}, not_contacted, unmatched_contacts}
- 지금 — part_mesh_map·mesh_report(좌석 열림) · contact_preview·dt_budget_advice(좌석 닫힘). 어댑터는 part_mesh_map 으로 bridge 엣지를 만들도록 짜여 있다
- 빠진 것 — 브리지가 실제로는 0건이다 — 어댑터가 응답에서 'rows' 키를 읽는데 도구 응답 키는 'parts' 다. 키가 맞아도 mesh_report 를 부르지 않아 stale 이 늘 true 라 same-as pid_map 단계가 돌지 않는다. contact_preview 는 미수집·좌석 닫힘
- 풀리는 도메인(2) — sim · rel
- 메커니즘 — interface.tied · new:process.data_comparability
- 질문 예 — 덱에 나갈 접촉 카드는 CAD 계면과 일치하는가 / 해석 모델의 pid 는 CAD 의 어느 파트인가
- 선행 — SIM: dyna pid 노드(K파일 캡처)
- 근거 — HR/adapters/mcad.py:523-526(_rows(…, 'rows')), 198-206 · DB rr_snapshot_calls part_mesh_map 응답({counts, parts[3]})·rr_ir_edges(bridge 0건) · disc part_mesh_map 16칸(parts)·contact_preview 31칸 · AS:644-655

### 간극·공차

#### MCAD-25 · 임의 두 파트 정밀 최소거리와 이웃 거리 표(0.5 mm 밖 포함)

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — measure_distance{a_path, b_path, min_gap[mm, 방향 없음 — 0 은 닿음과 겹침을 못 가름], bbox_gap[mm], centroid_distance[mm], 최근접 두 점}, nearest_parts{neighbors[]{b_path, min_gap[mm], bbox_gap[mm]}, bound_confirmed, stopped}, part_index.nearest_gap_mm·nearest_confirmed
- 지금 — measure_distance·nearest_parts(REST GET)·part_index(REST POST) — 좌석 닫힘. 우회로 — 과제 tol_config.clearance_gap 을 올려 재검출하면 더 먼 쌍도 IR 엣지가 된다 · 치수 기록부의 역할 쌍 최소 간극 키를 좌석이 compare_dimension 으로 읽는다 · IR bbox_world 로 상자 간극 근사
- 빠진 것 — IR 엣지 min_gap 은 0.5 mm 이하 쌍에만 있어 방사체–금속·진동원–센서·발열원–셀처럼 수 mm 떨어진 쌍은 값이 없다. 재검출 우회는 운영 조치이고 두 리비전 잣대가 같아야 한다(비용 unverified). 동결 규칙이 필요하다 — 최근접은 작업량 관문에 걸리면 bound_confirmed=false 로 나오므로 대상 파트를 역할로 한정하고 measure 잡으로 끝까지 잰 값만 싣고 미확정 행은 null 로 싣는다
- 풀리는 도메인(9) — mech · xd · rf · sh · soc · cam · disp · rel · pwr
- 메커니즘 — interface.clearance · interface.clearance_close · mechanical.vibration · thermal.hotspot · new:electrical.antenna_detune
- 질문 예 — 안테나 방사체에서 가장 가까운 도전체까지 최소거리와 그 상대는 무엇이며 리비전에서 줄었나 / IMU·마이크가 진동원에서 얼마나 떨어졌나 / AP 발열원에서 배터리 셀까지 최소거리는 얼마인가
- 선행 — MCAD-01 · MCAD-59
- 근거 — disc measure_distance 14칸·nearest_parts 22칸(bound_confirmed)·part_index(nearest_confirmed 한계) · GW list_interfaces clearance_range_note · GW get_project_meta clearance_gap 0.5 · GW compare_dimension()(키 32) · HR/adapters/mcad.py:17-19 · SF/app/rest.py:1933, 1954, 1973

#### MCAD-26 · 겹침 영역의 축방향 부호 간극

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — axis_gap{a_path, b_path, axis(x|y|z — 월드 축만), min_gap·median_gap·max_gap[mm, 음수는 침투], overlap_area[mm², 상자 겹침], overlap_ratio, hits, exact_min_distance[mm], min_gap_at[mm 월드], unreliable, one_sided}, section_report.plane_gaps[]{gap_in_plane[mm]}
- 지금 — axis_gap·section_report(좌석 닫힘, REST GET) · 치수 기록부가 axis_gap.min_gap·median_gap 을 키로 남기면 좌석이 compare_dimension 으로 읽는다 · 심사 extractor 로 두 파트 bbox_world 축 극값 차를 [d:] 로 정의할 수 있다(상자 근사)
- 빠진 것 — 어댑터 미호출·좌석 닫힘이라 '여유가 있다' 도 '없다' 도 인용할 값이 없다. 월드 축으로만 재서 자세가 다른 리비전끼리는 값이 달라지고 시트 바디가 낀 쌍은 null 이다. 실장 부품·패키지가 MCAD 솔리드로 온 판이 dev 에 없다(행 검증 인용). 스웰링 허용치·접점 작동 범위 같은 기준은 요구 등록이 선행이다
- 풀리는 도메인(9) — mech · soc · mem · pwr · rf · disp · cam · pcb · sh
- 메커니즘 — interface.clearance · interface.clearance_close · interface.tolerance_stackup · thermal.thermal_resistance · new:mechanical.battery_swelling_clearance
- 질문 예 — 셀 상면과 그 위 구조물 사이 두께 방향 간극이 수명말 스웰링 허용 증가분 이상인가 / AP 상면에서 쉴드캔 천장까지 Z 간극은 얼마이고 리비전에서 줄었는가 / 접점(C-clip·포고핀)의 눌림량이 작동 범위 안인가
- 선행 — MCAD-01 · MCAD-08 · MCAD-59
- 근거 — disc axis_gap 22칸(axis·overlap_area·min_gap 한계)·section_report(plane_gaps) · SF/core/dimensions.py:118-128 · GW compare_dimension() recordable.axis_gap · HR/adapters/mcad.py:17-19 · SF/app/rest.py:1705, 2058 · DB rr_dim_defs 0행

#### MCAD-27 · 면 기준 간극·밀착·파고듦 분포

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — clearance_field{part, face_normal(월드), against[]별 min·p10·median·p90·max[mm, 부호 없음], signed_min~signed_max[mm, 음수는 상대 안], contact_ratio·penetrating_ratio·unresolved_ratio[넓이 비율], sample_spacing[mm], partial, counterparts_unmeasured}. 동결용 고정 요약 — 상대별 {signed_min, p10, median, contact_ratio, penetrating_ratio} + sample_spacing·contact_eps·빌드 sha·geo_key
- 지금 — clearance_field(좌석 닫힘, REST POST) · run_job(kind='measure')로 끝까지 잰다(결과는 job_status 에만) · risk_screen 의 tim_not_compressed. 거친 답은 IR 엣지 kind·min_gap·penetration_depth
- 빠진 것 — 어댑터 미호출·좌석 닫힘·REST POST. 분포는 그대로는 diff 할 수 없다 — 표본 간격·작업량 관문에 딸리고 D-498 에서 칸의 뜻이 바뀌었다. 고정 요약 스칼라와 파라미터·빌드 패리티를 먼저 정해야 하고 치수 기록부도 이 도구를 안 받는다. 압착된 TIM 은 contact_ratio 0·penetrating_ratio 1 로 읽는다. 눌린 상태로 그려진 파트는 값이 뜻을 잃는다(MCAD-18). dev 게이트웨이 빌드(cb0c578)는 D-498 수정판임을 확인했다 — cae00 빌드는 unverified
- 풀리는 도메인(10) — mech · disp · cam · soc · mem · pwr · rf · sh · sim · rel
- 메커니즘 — thermal.thermal_resistance · thermal.hotspot · interface.clearance_close · mechanical.drop_stress · electrical.emi · new:interface.seal_compression
- 질문 예 — TIM 이 실제로 눌려 있나 — 밀착·파고든 넓이 비율과 중앙 간극은 / 커버글래스 에지와 프레임 립 사이 간극의 둘레 분포는 얼마이고 리비전에서 줄었나 / 디스플레이 배면과 배터리·쉴드캔 사이 간극이 가장 좁은 자리와 분포는
- 선행 — MCAD-01 · MCAD-18 · MCAD-59 · MCAD-05
- 근거 — GW glossary(tool='clearance_field') 39칸(contact_ratio·penetrating_ratio·signed_*·counterparts_unmeasured·job_call) · GW heaxstep_forge_system_capabilities build cb0c578 · SF/docs/REPLY-2026-09-24-press-region-cad.md:13-17, 59 · SF/app/rest.py:1747 · GW compare_dimension() recordable · HR 앱 코드 grep(clearance_field) 0건

#### MCAD-28 · 외관 이음매 갭·단차(flush)·돌출과 둘레 프로파일

**부분 · P1**

- 돌려줘야 하는 것 — 인접 외장 쌍의 이음매 호 길이 s[mm]에 따른 gap(s)[mm]·flush(s)[mm, 부호], min·max·편차, 구역. 축방향 돌출·매립 치수[mm](두 파트 bbox_world 축 극값의 차), 방사체에서 제품 외곽 6면까지 거리[mm]
- 지금 — 갭 분포는 clearance_field, 최소점 좌표는 measure_distance·axis_gap.min_gap_at(좌석 닫힘). 돌출·매립은 IR bbox_world 와 심사 extractor 로 지금도 정의할 수 있다
- 빠진 것 — 둘레를 따라간 위치별 프로파일과 인접 외면의 법선 방향 어긋남(단차)을 내는 도구가 없다. bbox_world 경로는 REST 채널에서만 살고 축정렬 상자라 곡면에서 틀리며 rr_dim_defs 가 0행이다
- 풀리는 도메인(5) — xd · mech · disp · cam · rf
- 메커니즘 — interface.tolerance_stackup · process.tolerance · mechanical.drop_stress
- 질문 예 — 외장 파트 사이 갭과 단차가 둘레를 따라 고른가 / 카메라 데코는 백커버 외면에서 얼마나 돌출하고 윈도우는 얼마나 매립돼 있나
- 선행 — MCAD-27 · MCAD-55
- 근거 — GW search_tools('외관 단차 flush 이음매 갭 seam gap step between exterior parts') 단차 도구 없음 · HR/ir_builder.py:574-582 · DB rr_dim_defs 0행·rr_ir_nodes bbox_world 3/12 · GW compare_dimension() not_yet(world_extents)

#### MCAD-29 · 공차 띠 입력·체인 정의·누적(worst-case·RSS)·실효 갭

**부분 · P0**

- 돌려줘야 하는 것 — 치수 키별 nominal[mm]·tol_minus·tol_plus[mm]·within_tol·deviation(지금 있음). 새로 필요한 것 — 체인 정의(링크 키 목록·부호), 누적값 worst_case·RSS[mm], 쌍별 effective_gap = min_gap − tol_stack − thermal_allow[mm]
- 지금 — 치수 기록부 record_dimension(key, nominal, tol_minus, tol_plus)(쓰기)·compare_dimension·compare_projects(좌석 열림). 심사 rr_dim_defs 의 const: 선언과 rr_requirements dim_limit
- 빠진 것 — 공차 값은 사람이 넣어야 한다(PMI 는 읽지 않는다 — MCAD-30). 누적과 실효 갭을 계산하는 도구가 어디에도 없다. 기록부의 공칭·공차는 rr_ir 에 안 실리고 심사 쪽 표는 0행이다. 열 여유는 재질명 → CTE 가 선행이다. xd 좌석 계약이 '공차 여유' 를 산출로 요구해 P0 로 두지만 입력이 비면 계산이 있어도 답이 안 나온다
- 풀리는 도메인(4) — xd · mech · disp · soc
- 메커니즘 — interface.tolerance_stackup · process.tolerance · thermal.cte_mismatch
- 질문 예 — 글래스-프레임 갭과 Z 스택 체인의 worst-case·RSS 여유는 얼마인가 / 0.5 mm 밖이지만 공차·열 여유를 빼면 모자라는 쌍은 무엇인가
- 선행 — MCAD-55 · MCAD-25 · MCAD-26 · MCAD-49 · OTHER: 요구·한계값 등록
- 근거 — GW compare_dimension()(row_detail 에 nominal·tol_minus·tol_plus) · SF/docs/SIDECAR_SPEC.md:246 · HR/assets/seat-contract.v1.json(contract.xd) · HR/assets/rules-seed.v1.json(R-002 fix_hint) · DB rr_dim_defs·rr_dim_vocab·rr_requirements 0행

#### MCAD-30 · PMI·GD&T(AP242) 읽기

**없음 · P1**

- 돌려줘야 하는 것 — 치수·면별 nominal[mm], tol_plus·tol_minus[mm], gdt_type(위치도·평면도·윤곽도)·tol_value[mm], datum_refs, 대상 면·축 식별자, 출처(pmi|sidecar|manual)
- 지금 — 없음 — 공차는 사람이 치수 기록부·사이드카로 넣는 길뿐이다
- 빠진 것 — StepForge 가 의도적으로 읽지 않고(비목표 표) 재직렬화에서도 유실된다. 사내 NX 내보내기에 PMI 가 실리는지는 unverified. 결정을 유지한다면 MCAD-29 의 전제(공차는 사람 입력, 데이텀 사슬은 표현 못 함)로 명기해야 한다
- 풀리는 도메인(4) — xd · mech · disp · std
- 메커니즘 — interface.tolerance_stackup · process.tolerance
- 질문 예 — 설계자가 도면에 적은 공차와 데이텀을 다시 치지 않고 모델에서 읽을 수 있는가
- 근거 — SF/docs/SIDECAR_SPEC.md:246 · SF/core/occ_compat.py:226 · SF/docs/NX_EXPORT_GUIDE.md:125

#### MCAD-31 · 축선·투영 기반 조회(관통 방향 거리·투영 겹침 이웃·광축 편심)

**부분 · P1**

- 돌려줘야 하는 것 — (a) 체결·돌출 축 연장선과 대상 파트의 교차 여부·끝점→대상 면 거리[mm]·사이 낀 파트 (b) 지목 파트 투영 안 이웃별 overlap_area[mm²]·min_gap[mm]·material (c) 두 축 사이 편심[mm]·각도차[deg]. 지금 있는 칸 — describe_interface.coaxial{axis_dir, axis_point, r_convex·r_concave, radial_clearance[mm], axial_overlap[mm]}
- 지금 — clearance_field(face_normal, against 비움 → 그 면이 보는 상대 전부)·axis_gap(월드 축과 나란할 때)·fastener_report(axis_point·axis_dir) — 좌석 닫힘. describe_interface.coaxial(좌석 열림, graph 잡 필요)
- 빠진 것 — 비스듬한 축의 광선 교차와 '사이 낀 파트' 조회가 없다. 상대별 투영 겹침 면적을 한 번에 내는 조회가 없고 재질이 null 이라 금속 여부를 못 가른다. coaxial 층은 동축으로 판정된 볼록–오목 짝의 반경 유격만 줘서 편심·각도차 칸이 없다
- 풀리는 도메인(3) — pwr · cam · disp
- 메커니즘 — interface.clearance_close · new:mechanical.battery_puncture · new:optical.axis_misalignment
- 질문 예 — 스크류 축 연장선이 셀을 지나는가, 끝에서 셀 면까지 거리는 얼마인가 / 무선충전 코일 투영 안에 들어오는 금속 파트는 무엇인가 / UPC 개구 중심과 렌즈 광축의 편심은 얼마인가
- 선행 — MCAD-21 · MCAD-49 · MCAD-01
- 근거 — GW glossary(tool='clearance_field') face_normal·against 한계 · disc axis_gap(hits·overlap_area 한계)·describe_interface 67칸 · 행 검증 인용(pwr-10 search_tools 2회 무결과)

#### MCAD-32 · 화각 원뿔 대 기구 내벽 간극

**없음 · P2**

- 돌려줘야 하는 것 — 입력 화각[deg]·입사동 위치[mm](모듈 사양), 출력 원뿔–내벽 최소 간극[mm]·최소 자리[mm 월드]·가리는 파트
- 지금 — 없음
- 빠진 것 — 원뿔 형상과 파트 사이 간극을 재는 도구가 없고 화각 사양을 담을 자리도 없다. 화각·입사동은 공급사 사양이라 입력은 side other 다
- 풀리는 도메인(1) — cam
- 메커니즘 — new:optical.fov_clearance
- 질문 예 — 화각 원뿔과 데코·윈도우 내벽 사이 최소 간극은 얼마인가
- 선행 — OTHER: 카메라 모듈 사양(화각·입사동)
- 근거 — GW list_tool_apps(heax-step_forge) 141종 이름(cone·fov 없음) · 행 검증 인용(disp-cam-45 search_tools 2회 0건, HR/requirements.py:32)

#### MCAD-33 · 조립성·서비스성 계산(삽입 경로 간섭·공구 접근·분해 깊이·스크류 혼용)

**없음 · P1**

- 돌려줘야 하는 것 — (a) 주어진 삽입 방향의 swept_clash[]{part, min_gap_mm} (b) 체결별 공구 접근 자유 원통 반경·길이[mm]·막는 파트·hidden_fasteners[] (c) 대상 모듈까지 disassembly_depth[단계]·removed_parts[]·irreversible_joints[개] (d) fastener_class{d, L[mm], count}·confusable_pairs·overshoot[mm]·part_behind
- 지금 — 재료만 있다 — fastener_report(axis_dir·head_seat·engagement_depth)·structure_report.subassemblies·what_holds·find_similar_parts·axis_gap
- 빠진 것 — 네 계산 모두 없다. 조립 순서·삽입 방향은 STEP 에 없는 공정 정보라 입력은 side other 다 — 원 행이 한 줄로 묶은 것을 출처별로 갈랐다. xd 계약은 '조립 순서·공차 여유·서비스성' 을 요구하는데 권장 도구 get_part_rules 는 메시·단순화 규칙 YAML 일 뿐이고 계획서도 근거 통로가 없다고 적는다. 비평의 P0 주장 대신 P1 로 둔다 — 통제 어휘에 해당 메커니즘이 없다. 계약 문구를 '주어진 삽입 방향의 조립 간섭·공차 여유·분해 깊이' 로 좁히거나 공정 입력 채널을 여는 결정이 필요하다
- 풀리는 도메인(4) — xd · mech · pwr · disp
- 메커니즘 — process.screw_torque · new:process.assembly_sequence · new:process.rework_access
- 질문 예 — 조립 순서상 나중에 가려지는 스크류·커넥터는 무엇인가 / 스크류를 조일 때와 풀 때 드라이버가 들어가는가 / 길이만 다른 스크류가 자리를 바꿔 들어가면 어디를 찌르는가
- 선행 — MCAD-21 · MCAD-19 · OTHER: 조립 순서·삽입 방향(공정 문서)
- 근거 — SF core·app grep(swept|insert_dir|disassembl) 형상 기능 0건 · GW list_tool_apps get_part_rules 설명 · HR/assets/seat-contract.v1.json(contract.xd) · PLAN:3478, 4865 · HR/assets/taxonomy.v1.json(mechanism 38종)

### 두께·국부 형상

#### MCAD-34 · 실제 최소 벽 두께와 위치

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — 정의별 thinnest[]{name, thickness[mm, 표면 법선 광선], at[mm×3 — 한 점], instances, parts}, 파트별 part_index.min_wall_mm[mm], 시트 바디는 null + 사유(두께는 사이드카 shell.thickness). 새로 필요한 칸 — 지정 위치의 국부 두께와 분포(min·p10·median)
- 지금 — thickness_report(REST GET)·part_index(REST POST)·slenderness_check.min_wall — 좌석 닫힘. 치수 기록부 기본 세트 '기본 최소 벽 {role}' 16종(좌석이 compare_dimension 으로 읽음). check_claim(scalar, part_index.min_wall_mm)이 열린 우회로
- 빠진 것 — IR 의 min_dim 은 정의 bbox 최소 변이라 평판에서만 두께다 — 리브 달린 하우징·곡면 글라스에서는 벽이 얇아져도 이벤트가 안 선다. 실제 벽 두께를 실어도 R-003·thin_ratio·part.thickness_changed 가 min_dim 을 읽으므로 소비처 전환을 같이 해야 한다. 도구는 최소 한 점만 내 '그 자리' 두께(레이돔·카메라 윈도우)에는 부족하다. 판 전체 수집 비용은 정의 수에 비례한다(단가는 재확인하지 않음)
- 풀리는 도메인(8) — mech · sim · material · disp · cam · rf · soc · xd
- 메커니즘 — mechanical.bending · mechanical.buckling · process.tolerance · mechanical.drop_stress
- 질문 예 — 프레임·브래킷·백커버의 최소 벽 두께와 그 자리는 어디이고 리비전에서 얇아진 파트는 / 접착층·테이프의 실제 두께(본드라인)는 얼마인가 / 안테나 직상 커버의 국부 벽두께는 얼마인가
- 선행 — MCAD-59 · MCAD-12
- 근거 — HR/adapters/mcad.py:643 · HR/diff.py:1362-1370 · HR/state.py(thin_ratio 'min_dim 근사') · HR/assets/rules-seed.v1.json(R-003 node.min_dim) · disc thickness_report 12칸(at 한계) · GW compare_dimension() recordable.part_index.min_wall_mm · SF/app/rest.py:2210, 1973

#### MCAD-35 · 적층 환원(층 순서·층 두께·층간 간극)

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — is_stack·reason, axis(x|y|z)·axis_agreement, layers[]{part, order, thickness[mm], material(이름), range[mm], area[mm²]}, gaps[]{between, gap[mm, 음수는 겹침], contact_area[mm²], overlap_ratio}, interference[]{penetration_thickness[mm]}, thickness_check{sum_layers, bbox_along_axis, agree}, for_laminate_analysis{laminae, total_thickness_mm}
- 지금 — stackup_profile(좌석 닫힘, REST POST). 층이 별도 솔리드면 각 파트 min_dim 과 이웃 계면은 IR 에 있다
- 빠진 것 — 어댑터 미호출·좌석 닫힘·REST POST. 월드 축 셋 중 하나로만 답하고 이웃 층끼리만 본다. 안 닿는 묶음은 is_stack=false 와 사유만 나온다. 재질은 이름뿐이다. 층이 솔리드로 분리돼 있어야 한다(MCAD-12). 결과를 리비전끼리 견주는 도구가 없어 층 순서·간극 변화 이벤트가 없다
- 풀리는 도메인(9) — disp · mech · material · sh · soc · mem · pwr · rf · sim
- 메커니즘 — thermal.cte_mismatch · thermal.thermal_resistance · interface.adhesive_area · process.warpage · new:mechanical.fold_crease_strain
- 질문 예 — 디스플레이 적층의 층 순서·층별 두께·층간 간극은 얼마인가 / AP 에서 TIM·쉴드캔·VC·프레임까지 열경로의 층 두께·접촉 면적·공기층은 / 무선충전 코일–차폐 시트–셀의 적층 순서와 간극은
- 선행 — MCAD-12 · MCAD-49 · MCAD-59
- 근거 — disc stackup_profile 47칸(axis·gaps 한계) · SF/app/rest.py:2188 · HR/adapters/mcad.py:17-19 · 행 검증 인용(material-sh-27 laminate backend_down)

#### MCAD-36 · 리브·보스 형상 치수

**도구는 있음 · 스냅샷 미수집 · P1**

- 돌려줘야 하는 것 — features[]{feature(rib|boss|unclassified), centroid[mm], height_mm, thickness_mm, length_mm, root_thickness_mm, tip_thickness_mm, draft_ratio(각도 아님), height_over_thickness, radius_mm(보스), cylinder_tilt_deg, nearest_feature_mm}, counts
- 지금 — rib_boss_features(좌석 닫힘, REST GET) — 행의 radius_mm·thickness_mm·height_mm 는 치수 기록부에 남길 수 있다
- 빠진 것 — 어댑터 미호출·좌석 닫힘. 자세 불변이 아니다. 보스 살두께는 fastener_report 와 조인해야 나온다. 실물에 리브·보스가 있는 판이 없어 재현율 근거가 합성 픽스처뿐이다(행 검증 인용)
- 풀리는 도메인(4) — mech · xd · material · pwr
- 메커니즘 — process.tolerance · mechanical.bending · process.screw_torque
- 질문 예 — 리브의 높이/두께 비와 뿌리 두께는 얼마인가 / 보스 반경·높이·이웃 벽까지 거리는 얼마이고 보스 크랙 후보는 어디인가
- 선행 — MCAD-59
- 근거 — disc rib_boss_features 59칸(draft_ratio 한계) · GW compare_dimension() recordable.rib_boss_features · SF/app/rest.py:963

#### MCAD-37 · 구멍 둘레 살 폭·코너 근접

**도구는 있음 · 스냅샷 미수집 · P1**

- 돌려줘야 하는 것 — holes[개], min_hole_to_edge·min_hole_to_hole[mm], worst{kind, width, center, radius}, skipped_voids[개], hole_list[]{center[mm 월드], axis, radius_mm, distance_mm(OBB 꼭짓점까지)}
- 지금 — ligament_check·corner_proximity(좌석 닫힘, REST GET) — corner_proximity 행은 치수 기록부에 남길 수 있다
- 빠진 것 — 어댑터 미호출·좌석 닫힘. 둘러싸인 원형 구멍만 센다 — 트랙형·사각 라운드 카메라 홀과 슬롯은 skipped_voids 로 수만 나온다(MCAD-38)
- 풀리는 도메인(3) — cam · sh · mech
- 메커니즘 — mechanical.drop_stress · mechanical.bending
- 질문 예 — 후면 글라스 카메라 홀 가장자리에서 외곽·인접 홀까지 최소 살 폭은 얼마인가 / 기구 쪽 음향 포트 구멍의 중심·반경은 얼마인가
- 선행 — MCAD-59
- 근거 — disc ligament_check 26칸(skipped_voids 한계)·corner_proximity 38칸 · SF/core/profile.py:608-620 · SF/app/rest.py:939, 1877

#### MCAD-38 · 슬롯·비원형 개구·노치·관통 절개 치수

**없음 · P1**

- 돌려줘야 하는 것 — openings[]{kind(hole|slot|notch|slit), length_mm, width_mm, center[mm 월드], through(bool), filler_part}, longest_slot_mm, 외부로 열린 개구 목록
- 지금 — ligament_check·corner_proximity(원형 구멍만, 슬롯은 수만) · section_area.regions · IR status_flags.multi_solid
- 빠진 것 — 슬롯·노치의 길이·폭·위치를 내는 칸이 어느 도구에도 없다. 한 파트 안 솔리드 사이 거리를 재는 도구도 없어 한 파트로 내보낸 프레임의 안테나 슬릿은 잴 수 없다(세그먼트가 따로 왔으면 MCAD-25 로 나온다)
- 풀리는 도메인(4) — mech · rf · rel · cam
- 메커니즘 — electrical.emi · mechanical.bending · material.moisture · new:electrical.antenna_detune
- 질문 예 — 쉴드캔 벽·커버의 개구 슬롯 최장 길이는 얼마인가 / 메탈 프레임 분절(슬릿)의 위치와 폭이 리비전에서 달라졌는가
- 선행 — MCAD-22
- 근거 — disc ligament_check(skipped_voids '그 자리의 폭은 이 도구가 안 잰다') · SF/core/profile.py:608-620 · 행 검증 인용(mech-xd-22·rf-02·rf-16 search_tools 무결과, SF grep slot|obround 0건)

#### MCAD-39 · 단면 성질 분포·강성 급변·무지지 스팬

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — section_profile{axis(사람이 준다), sections[]{position[mm], area_mm2, I[mm⁴], principal_I, Z[mm³]}, weak_section{by_area, by_second_moment}}, stiffness_jump{jumps[]{from, to, I_ratio, area_ratio, EI_from·EI_to[N·mm²]}, E_unavailable}, slenderness_check{extents{min, mid, max}[mm], min_wall, aspect_over_wall, unsupported{span[mm], at, supports}}
- 지금 — section_profile·stiffness_jump(REST GET)·slenderness_check(REST POST) — 전부 좌석 닫힘
- 빠진 것 — 어댑터 미호출·좌석 닫힘. 하중축을 도구가 정하지 않는다(수집하려면 제품 프레임의 긴 축으로 고정). 비틀림 상수 J 가 없고 EI 는 등록 재질이 있어야 나온다. 받침은 가정이라 조립 접촉 지지는 사람이 준다. 자세 불변 여부는 unverified
- 풀리는 도메인(5) — mech · sim · pcb · cam · sh
- 메커니즘 — mechanical.bending · mechanical.buckling · mechanical.vibration
- 질문 예 — 세트 길이축을 따라 굽힘에 가장 약한 단면은 어디이고 강성이 급변하는 자리는 / 보드 지지점 사이 무지지 스팬은 얼마인가
- 선행 — MCAD-08 · MCAD-49 · MCAD-59
- 근거 — disc section_profile 36칸(axis 한계)·stiffness_jump 37칸·slenderness_check 33칸(unsupported 한계) · SF/app/rest.py:982, 2051, 2174

#### MCAD-40 · 굽힘 형상(반경·두께·각도)

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — bends[]{radius_inner·radius_mid·radius_outer[mm], thickness[mm], angle_deg, axis, axis_point[mm], width[mm], arc_length_mid[mm], basis}, is_bent_plate, for_bending_analysis{thickness_mm, bend_radius_mm, curvature_1_per_mm}, not_bent_reasons
- 지금 — bend_profile(좌석 닫힘, REST GET) — B-spline 면도 적합·곡률 경로로 읽는다
- 빠진 것 — 어댑터 미호출·좌석 닫힘이라 IR 에 반경 속성이 없고 계획서 실례의 d:hinge_radius 를 만들 추출식이 없다. 치수 기록부도 굽힘 반경을 아직 못 받는다. 굽힌 솔리드가 STEP 에 있어야 하고 저장된 한 자세만 본다. is_bent_plate 는 판금이라는 뜻이 아니다. 보강재 끝단–굽힘 시작점 거리는 직접 나오지 않는다
- 풀리는 도메인(9) — disp · mech · cam · pcb · material · sim · rel · xd · pwr
- 메커니즘 — mechanical.fatigue · mechanical.bending · new:mechanical.fold_crease_strain · new:mechanical.fpcb_bend_radius
- 질문 예 — 접힘부 내측 곡률반경과 굽힘 각도는 얼마이고 리비전에서 바뀌었나 / FPCB·패드 벤딩부의 굽힘 반경/두께 비는 얼마인가
- 선행 — MCAD-12 · MCAD-59
- 근거 — disc bend_profile 35칸(is_bent_plate·basis 한계) · GW compare_dimension() not_yet('bend_profile 의 굽힘 반경') · PLAN:2150 · SF/app/rest.py:1714 · HR/ir_builder.py:574-582

#### MCAD-41 · 내측 코너 필렛 반경·노치

**없음 · P1**

- 돌려줘야 하는 것 — 오목 모서리별 위치[mm×3], 반경[mm](0 이면 날모서리), 두 면 사이 각[deg], 인접 최소 벽[mm], r/t 비, 파트별 min_concave_radius[mm]
- 지금 — bend_profile 은 판 굽힘 반경만, ligament_check 는 구멍 살 폭만 낸다. core/profile.py 는 안쪽 필렛을 '구멍이 아닌 것' 으로 가르는 라벨에만 쓴다
- 빠진 것 — 모서리 반경을 내는 도구가 141종에 없다. 사출 프레임·글라스·힌지 파트의 균열 기점은 반경이 정하는데 값이 없어 '응력 집중 우려' 가 위치 없는 문장으로 남는다. 두 비평 제안(P1·P2)을 하나로 합쳤다
- 풀리는 도메인(5) — mech · rel · disp · sim · xd
- 메커니즘 — mechanical.drop_stress · mechanical.fatigue · mechanical.bending
- 질문 예 — 낙하·반복 하중에서 응력이 몰릴 날모서리와 작은 필렛이 어디에 있는가
- 선행 — MCAD-22
- 근거 — GW search_tools('필렛 반경 내측 코너 노치 응력 집중 fillet radius concave edge') 해당 도구 없음 · SF core·app grep(fillet|chamfer|edge_radius) 0건 · SF/core/profile.py:612-617

#### MCAD-42 · 스냅핏·후크 형상

**없음 · P1**

- 돌려줘야 하는 것 — hook id, engagement(걸림량)[mm], arm_length[mm], root_thickness[mm], 조립 시 필요 변위[mm], 굽힘 변형률 추정[%], 후크 개수·둘레 분포, 걸림 상대 파트
- 지금 — rib_boss_features 는 리브·보스만 가른다. 결합 수단은 사람이 set_joint·set_interface·역할로 남길 수 있다
- 빠진 것 — 후크 형상을 식별·계측하는 기능이 없고 역할 16종에도 후크·스냅핏이 없다
- 풀리는 도메인(2) — xd · mech
- 메커니즘 — mechanical.fatigue · process.tolerance · interface.tied_loss
- 질문 예 — 후크가 조립 중 부러지지 않고 낙하에서 빠지지 않을 만큼 걸려 있는가
- 선행 — MCAD-22 · MCAD-49
- 근거 — SF core·app grep(snap_fit|snapfit|스냅핏|후크|hook) — build-hook 문자열뿐 · disc rib_boss_features(feature enum) · SF/core/data/part_ontology.yaml

#### MCAD-43 · 사출·판금 제조성 지표(구배·언더컷)

**부분 · P1**

- 돌려줘야 하는 것 — 파트별 draft_angle_deg(면별 최소 구배각), undercut(bool)·언더컷 면 위치, 판금 R_over_t. 이미 있는 재료 — min_wall_mm(MCAD-34), 리브 height_over_thickness·draft_ratio(MCAD-36), bend radius_inner·thickness(MCAD-40)
- 지금 — thickness_report·rib_boss_features·bend_profile·ligament_check·slenderness_check(좌석 닫힘) · risk_screen 의 thin_wall·bend_formability
- 빠진 것 — 원 행의 '공정별 제조성 지표와 한계값 대조' 를 구현 단위로 갈랐다. CAD 가 줄 것 중 없는 것은 구배각·언더컷이다. 한계값은 StepForge 가 의도적으로 두지 않는다(사전의 문턱이 전부 false) — 한계는 공정 사양 입력(side other), 파팅라인·게이트·웰드라인은 금형사 자료다
- 풀리는 도메인(3) — xd · mech · material
- 메커니즘 — process.tolerance · new:process.molding_dfm
- 질문 예 — 사출 최소 살두께·빼기 구배·언더컷 기준을 벗어난 파트는 무엇인가 / 판금 최소 R/t 기준을 벗어난 굽힘은 어디인가
- 선행 — MCAD-34 · MCAD-36 · MCAD-40 · OTHER: 공정 한계값 표
- 근거 — SF core·app grep(draft_angle|undercut|parting) 0건 · SF/core/data/failure_modes.yaml:5-8 · disc rib_boss_features.draft_ratio 한계

#### MCAD-44 · 형상 건전성(위상 유효성·슬리버·시트 바디)

**부분 · P1**

- 돌려줘야 하는 것 — 정의별 detail[]{name, valid, solids, faces, freeform_ratio, short_edges, sliver_faces, min_edge[mm], findings}, invalid[개], sheet_or_shell[개]. IR 에 있는 것 — status_flags(multi_solid·missing_geometry·construction_only·volume_null)
- 지금 — geometry_health(REST GET)·precheck_report(잡 결과 읽기) — 좌석 닫힘. mesh_report.parts[].thickness 는 좌석 열림
- 빠진 것 — 플래그 넷은 수집되나 위상 유효성·슬리버·자유곡면 비율·시트 바디 두께 유무는 미수집이다. 플래그 일부는 REST 채널에서만 선다. 형상 결함에서 온 가짜 간섭·가짜 얇은 벽을 설계 리스크와 가를 근거가 없다
- 풀리는 도메인(2) — xd · sim
- 메커니즘 — new:process.geometry_integrity
- 질문 예 — 유효하지 않은 솔리드·시트 바디·슬리버 면·다중 솔리드 파트는 어느 것인가
- 선행 — MCAD-58
- 근거 — HR/adapters/mcad.py:658-673, 784-794 · disc geometry_health 33칸 · SF/app/rest.py:1831

### 실링·접착

#### MCAD-45 · 실링·접착 경로 추출(폐루프·위치별 폭·끊김·이음 횡단)

**없음 · P0**

- 돌려줘야 하는 것 — 경로별 loop_closed(bool), path_length_mm, 호 길이 s 에 따른 width(s)[mm], width_min_mm 와 그 좌표[mm 월드], width_p10·median[mm], breaks[]{length_mm, at}, 안착면 파트 경계 횡단 crossings[]{s, seat_part_a·b, step[mm], gap[mm]}, 접합 띠 최장 스팬 bond_span_max[mm]
- 지금 — 쌍당 스칼라만 있다 — band_width·contact_area_est(IR 수집), 검출 행의 face_pairs(explain_kind·render_interface 로만 보임), clearance_field 의 contact_ratio, leak_report
- 빠진 것 — 행들의 상태가 갈렸다(partial 2·missing 2). 다시 확인해 missing 으로 정한다 — 폐루프·위치별 폭·끊긴 구간·이음 횡단을 내는 기능이 141종과 소스 어디에도 없다. 쌍당 스칼라와 밀착 비율은 MCAD-14·27 이 진다. band_width 는 면 짝 폭의 최댓값이라 가장 좁은 곳을 말하지 않고 고리 모양 접촉에서는 비드 폭이 아니며, contact_area_est/band_width 는 띠 길이가 아니다
- 풀리는 도메인(7) — mech · disp · material · rel · rf · sh · xd
- 메커니즘 — interface.adhesive_area · material.moisture · interface.tied_loss · thermal.cte_mismatch · electrical.emi · new:interface.seal_path_continuity
- 질문 예 — 방수 접착(가스켓) 경로가 끊김 없이 닫혀 있나, 최소 유효 접착폭은 얼마이고 어디인가 / 쉴드캔–PCB 접지 접촉이 끊긴 구간의 최대 길이는 / 실링 띠가 이종 파트 이음을 몇 번 건너고 그 자리 단차는 얼마인가
- 선행 — MCAD-01 · MCAD-14
- 근거 — SF core·app grep(loop_closed|closed_loop|seal_path|band_gaps) 0건 · disc list_interfaces.band_width 한계 · SF/app/db.py:54-59 · HR/assets/seat-contract.v1.json(_common) · 행 검증 인용(search_tools 실링·접착 경로 표현 무결과)

#### MCAD-46 · 닫히지 않은 틈 목록

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — gaps[개], widest_gap[mm], gap_method(detected|measured), pairs[]{a_path, b_path, gap[mm]}, suggested_seal_gaps[mm], container
- 지금 — leak_report(container, max_gap) — 좌석 닫힘, REST GET. 스냅샷 clearance 엣지는 0.5 mm 이하만 담는다
- 빠진 것 — 어댑터 미호출·좌석 닫힘. 틈의 크기만 내고 실 라인 연속성·압축률·등급 판정은 없다. 간극 0 인 쌍은 빠지고 사이에 다른 파트가 끼어 있어도 쌍으로 센다
- 풀리는 도메인(5) — rel · sh · mech · disp · cam
- 메커니즘 — material.moisture · interface.clearance · new:interface.seal_path_continuity
- 질문 예 — 음향 챔버·방수 실링이 닫혀 있는가 — 가장 큰 틈은 어느 쌍·몇 mm 인가 / 패널 에지·카메라 개구 둘레 실링에 남은 틈이 있는가
- 선행 — MCAD-01
- 근거 — disc leak_report 15칸(gaps 한계) · SF/app/rest.py:1869 · HR/adapters/mcad.py:17-19

#### MCAD-47 · 갇힌 공동(체적·경계 파트·통로)과 밀폐 안팎 라벨

**부분 · P0**

- 돌려줘야 하는 것 — cavities[]{id, volume_mm3, bounding_parts[], container, region(hull|box), seal_gaps[mm]}, passages[]{between, area_min_mm2, length_mm}, 파트·계면별 enclosed(bool)·cavity_id, Δvolume[%]. 지금 있는 칸 — list_artifacts.stats{cavity_volume, total_void_volume, solids_kept, residual}
- 지금 — build_cavity(잡 — 카탈로그 분류 '수정') → cavity_step · list_artifacts(좌석 열림 — 이미 만든 공동의 stats) · section_area · leak_report
- 빠진 것 — 비평 지적대로 have_not_ingested 가 아니다 — build_cavity 는 잡이라 어댑터도 좌석도 걸 수 없고, 사람이 돌린 산출물을 스냅샷으로 읽는 통로가 없다. 산출물은 과제당 한 벌이라 스피커·리시버·마이크 챔버를 따로 보관하지 못한다. 공동별 체적·경계 파트·공동 간 통로·밀폐 안팎 라벨을 답하는 질의는 없다. 리비전 비교는 컨테이너·파라미터 동일 표식이 필요하다
- 풀리는 도메인(5) — sh · material · rel · mech · cam
- 메커니즘 — material.moisture · material.corrosion · new:acoustic.back_volume
- 질문 예 — 스피커·리시버 백볼륨 체적은 얼마이고 리비전에서 얼마나 변했나 / 기압 센서가 스피커 백볼륨·배터리와 같은 밀폐 공동을 공유하는가 / 사운드 포트의 길이와 최소 단면적은 얼마인가
- 선행 — MCAD-46 · MCAD-59
- 근거 — GW heaxstep_forge_system_capabilities catalog '수정' 에 build_cavity · GW run_job 스키마(kind cavity) · disc list_artifacts(stats) · GW compare_dimension() recordable(공동 없음) · 행 검증 인용(SF/core/cavity.py:80-92, SF/core/job_worker.py:845-851)

#### MCAD-48 · 압축률·홈 충전율(실·가스켓·쿠션·TIM)

**부분 · P1**

- 돌려줘야 하는 것 — compression_pct = 축방향 겹침 ÷ 자유 단면 높이, fill_pct = 실 단면적 ÷ 홈 단면적. 재료값 — penetration_thickness[mm], layers[].thickness[mm], axis_gap.min_gap[mm, 음수], section_area.total_area_mm2[mm²]
- 지금 — stackup_profile 간섭 모드(층 thickness 와 음수 gap·penetration_thickness 를 한 응답에)·axis_gap·section_area(좌석 닫힘) · list_interfaces.penetration_thickness(좌석 열림, IR 미수집)
- 빠진 것 — 압축률·충전율 칸이 없고 재료값이 흩어져 있다. penetration_depth 는 하한이라 압축량이 아니다. 실을 압축 후 형상으로 그렸으면 간섭이 0 이라 계산할 수 없다 — 모델링 상태 표식(MCAD-18)이 전제다
- 풀리는 도메인(6) — mech · disp · material · sh · rel · rf
- 메커니즘 — material.creep · interface.interference · new:interface.seal_compression
- 질문 예 — 가스켓·오링의 압축률과 홈 충전율은 얼마인가 / 상시 압축을 받는 폼·스펀지·TIM 은 어느 것이고 압축량은 얼마인가
- 선행 — MCAD-15 · MCAD-18 · MCAD-26 · MCAD-35
- 근거 — disc stackup_profile(interference·penetration_thickness·penetration_depth)·section_area 17칸 · HR/adapters/mcad.py:830-833

### 재질·질량

#### MCAD-49 · 파트 재질명·밀도(사람·사이드카 지정 포함)와 재질 변경 이벤트

**부분 · P0**

- 돌려줘야 하는 것 — 인스턴스별 material(이름), from(manual|step|sidecar), density(파일 값 그대로)·density_unit, 이벤트 part.material_changed{before, after}, 판 단위 material_null 수·비율
- 지금 — REST tree.json shape_defs.material·density → rr_ir part attrs·sig:counts.material_null·rr_diff part.material_changed. list_parts·find_parts·describe_part.material{step, manual}·compare_revisions.material_changed(좌석 열림) · set_part_metadata(material=)·사이드카(쓰기)
- 빠진 것 — 뿌리가 둘이다. ① 데이터 — 관측한 파트 전부가 재질·밀도 null. ② 통로 — REST 정본 채널의 어댑터는 tree.json shape_defs.material(STEP 이 담아 온 값)만 읽는다. 사람·사이드카가 적은 재질은 REST /parts 의 COALESCE(n.material, s.material)에 있고 어댑터는 그 응답을 받으면서 id 대응에만 쓴다 — 재질을 채워도 정본 채널 스냅샷에는 null 로 남는다(코드 대조, 실주행 재현은 안 함). 재질명이 비면 물성 조회 키·질량·CTE·갈바닉·도전체 판정이 한꺼번에 죽는다
- 풀리는 도메인(9) — material · mech · disp · soc · rf · sim · rel · xd · pwr
- 메커니즘 — material.property_uncertain · material.supplier_change · thermal.cte_mismatch · mechanical.mass · material.corrosion
- 질문 예 — 리프 파트마다 지정된 재질명·밀도는 무엇이고 재질이 비어 있는 파트는 몇 개인가 / base→target 사이 재질이 바뀐 파트는 어느 것인가 / 방사체 인접 파트가 금속인가 수지인가
- 선행 — MCAD-12
- 근거 — HR/adapters/mcad.py:392-394, 451-454, 644-646 · SF/app/rest.py:544-566, 569-581 · SF/app/mcp_server.py:1040 · SF/core/model.py:41 · DB rr_snapshot_calls REST /parts 응답 행(material 칸)·rr_ir_nodes(material 0/12) · GW describe_part(material.step·manual null)·list_unknowns no_material 12/12

#### MCAD-50 · 재질 해석표(어느 카드로 풀리나)와 의심 공유값

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — parts·resolved·unresolved·without_material[개], detail[]{part, path, material, from, resolved_as, source(local|db_json|materialtwin), mat_type}, suspect_shared_values{물성키: [{value, shared_by[], count}]}
- 지금 — resolve_materials(좌석 닫힘, REST GET) · material_lookup·material_sources·list_local_materials·mesh_report.materials(좌석 열림)
- 빠진 것 — 어댑터 미호출이라 IR·diff 에 없다. 과제가 쓴 재질만 보는 resolve_materials 는 좌석 닫힘이고 열린 list_local_materials 는 서버 오버레이 전체다. '찾았다' 는 '맞다' 가 아니다(CAD 기본값도 찾는다). MaterialTwin 갈래가 dev 에서 답하지 않는 사례가 있다(원인 unverified — 행 검증 인용)
- 풀리는 도메인(3) — material · sim · mech
- 메커니즘 — material.property_uncertain
- 질문 예 — CAD 재질명이 물성 카드로 풀리는가 — 어느 출처의 어떤 카드로 풀렸고 못 푼 이름은 / CAD 기본값이 진짜 물성인 척 실려 온 재질이 있는가
- 선행 — MCAD-49 · OTHER: 물성 DB(MaterialTwin)
- 근거 — disc resolve_materials 21칸(resolved 한계) · SF/app/rest.py:2021 · AS:2061-2105 · 행 검증 인용(GW list_local_materials 5건 from=cad_default)

#### MCAD-51 · 질량·무게중심·관성(출처 있는 밀도)

**부분 · P0**

- 돌려줘야 하는 것 — mass_estimate{total_mass(mm³ × density_unit), center_of_mass[mm], known·unknown[개], unknown_parts[]{why}, parts[]{volume_mm3, material, file_density}}, rigid_properties{centroid[mm], inertia_about_centroid(mm⁵, 밀도 1 기준), principal, principal_axes, radius_of_gyration}
- 지금 — mass_estimate(좌석 열림 — densities 인자)·describe_part.mass(좌석 열림)·bom_export·rigid_properties(좌석 닫힘) · IR volume·density·sig:scale.mass_est
- 빠진 것 — 밀도 출처가 없다(12/12 null — mass_est 신호는 리프 전부의 밀도가 있어야 선다). mass_estimate·bom_export 는 resolve_materials 가 찾은 재질의 밀도를 읽지 않는다. STEP 밀도는 파일 단위 그대로다. 내부가 찬 덩어리 솔리드(모듈·셀)는 승인원 질량을 사양으로 받아야 한다. 옛 파싱분은 volume 이 null
- 풀리는 도메인(7) — sim · material · cam · pwr · sh · mech · passive
- 메커니즘 — mechanical.mass · mechanical.drop_stress · mechanical.vibration
- 질문 예 — 총 질량·무게중심이 해석 모델과 몇 % 차이인가 / 카메라·LRA 모듈 질량과 고정점 대비 편심은 / MLCC 장축이 보드 굽힘 주방향과 나란한가
- 선행 — MCAD-49 · MCAD-50
- 근거 — HR/state.py:419-424 · DB rr_ir_nodes(density·volume 0/12) · disc mass_estimate 15칸·resolve_materials.resolved 한계 · GW describe_part(…) mass 블록 · AS:644-655

#### MCAD-52 · 계면 쌍 × 재질 조합(이종재료·이종금속)

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — by_material[]{a, b(재질명), pairs[개], by_kind{tied, touching, clearance, interference}, contact_area[mm²]} 또는 엣지별 material_a·material_b
- 지금 — interface_summary(by='material')(좌석 닫힘, REST GET). IR 안에서 엣지와 노드 attrs.material 을 조인하면 같은 표가 나온다
- 빠진 것 — 도구는 좌석 닫힘·미수집이고 IR 조인을 내는 신호가 없다. 재질명이 null 이면 전부 '(없음)' 한 칸이다. 이름이지 물성이 아니다
- 풀리는 도메인(3) — material · mech · rel
- 메커니즘 — thermal.cte_mismatch · material.corrosion
- 질문 예 — 접합·접촉 쌍마다 양쪽 재질 조합은 무엇이고 CTE 차가 큰 쌍은 어디인가 / 닿아 있는 이종 금속 쌍은 어느 것인가
- 선행 — MCAD-49 · MCAD-14
- 근거 — disc interface_summary 52칸(by_material 한계) · HR/state.py:344-348 · SF/app/rest.py:1859

#### MCAD-53 · 표면처리·도금과 재질 등급 축

**없음 · P1**

- 돌려줘야 하는 것 — 파트·면 단위 surface_finish(anodize|plating|PVD…)·coating_thickness[µm]·finish_scope(part|face), 재질 등급 축 grade·supplier·temper·filler_pct·spec_no
- 지금 — 재질 이름 한 칸과 자유 항목뿐 — set_part_metadata 의 tags·note·meta, 사이드카 extras·part_number
- 빠진 것 — 표면처리 전용 칸이 도구·사이드카 어디에도 없고 등급·열처리 축은 사이드카 규격의 미결 질문이다. 자유 항목에 적어도 어댑터가 tags·meta 를 싣지 않는다. 갈바닉 쌍은 표면층이 정하고 같은 이름의 등급·공급사 변경은 형상 diff 가 0 이다
- 풀리는 도메인(4) — material · mech · xd · rel
- 메커니즘 — material.corrosion · material.supplier_change
- 질문 예 — 닿아 있는 이종 금속 각 면의 표면처리는 무엇인가 / 재질 이름은 같은데 등급·공급사·조질이 바뀌었는가
- 선행 — MCAD-49
- 근거 — SF core·app grep(surface_finish|anodiz|plating) 0건 · SF/docs/SIDECAR_SPEC.md:84-90, 238, 253 · HR/adapters/mcad.py:625-655

### 연성 부품·케이블

#### MCAD-54 · 연성 부품(FPCB·케이블) 경로 길이·여유·굴곡

**없음 · P1**

- 돌려줘야 하는 것 — fpcb·cable{path_length_mm(중심선), slack_mm(직선거리 대비 여유), min_bend_radius_mm·at[mm 월드], outer_diameter_mm, clip_points[]}, 자세 간 경로 길이 차[mm]
- 지금 — bend_profile(굽은 채 모델링된 판 솔리드 — MCAD-40) · 리테이너 눌림은 interference 엣지(MCAD-14·15)
- 빠진 것 — 행들의 상태가 갈렸다(partial·missing). 경로·중심선·여유 길이를 내는 도구가 없고 스윕된 관·케이블은 다루지 않으며 온톨로지에 cable·coax·fpcb 역할이 없어 missing 으로 둔다. StepForge 는 저장된 한 자세의 강체 솔리드만 본다
- 풀리는 도메인(6) — xd · mech · disp · cam · rf · pwr
- 메커니즘 — mechanical.fatigue · new:mechanical.fpcb_bend_radius · new:interface.connector_retention
- 질문 예 — FPCB 가 물리는 BTB 커넥터까지 길이 여유가 있는가 / 마이크로 동축 케이블의 경로 길이와 최소 굽힘 반경은 얼마인가
- 선행 — MCAD-01 · MCAD-11 · MCAD-40
- 근거 — SF/core/data/part_ontology.yaml(pcb 동의어 FPCB, cable·coax 없음) · disc bend_profile(arc_length_mid) · 행 검증 인용(disp-cam-23·rf-25 search_tools 무결과)

### 명명 치수·요구

#### MCAD-55 · StepForge 치수 기록부 → 스냅샷 dims_named

**도구는 있음 · 스냅샷 미수집 · P0**

- 돌려줘야 하는 것 — 키별 key, tool.field, value, unit, nominal·tol_minus·tol_plus, within_tol, deviation, status(ok|no_value|error), stale(bool), targeting_changed, units_suspect, spot(잰 두 점), geo_key·build, measured_at. 기본 세트 31치수 — 외곽 3변, 파트 수, 총 질량, 역할 쌍 최소 간극 10, 역할별 최소 벽 16
- 지금 — record_dimension·apply_dimension·run_job(kind='dimension')(쓰기) · compare_dimension·compare_projects(좌석 열림) · 기록 가능 칸 measure_distance.min_gap, axis_gap.min_gap·median_gap, part_index 의 volume·area·min_wall, mass_estimate, where_is 외곽, rib_boss_features 행, corner_proximity 행
- 빠진 것 — 두 치수 장부가 따로 논다 — 심사는 기록부를 안 읽고 자체 표가 0행이라 [d:] 인용과 dim.named_changed 가 비어 있다. 잇는 방향은 맞지만 통로가 막혀 있다. REST 판이 POST 라 GET 전용 어댑터로 못 읽고 MCP 판은 300초 캐시된다. 지목 방식이 다르다(기록부는 역할·글롭, 심사 extractor 는 ckey·asm) — 이름 대응 규칙과 '낡은 기록은 null' 규칙이 필요하다. 값을 채우는 apply_dimension 은 쓰기라 사람이나 잡이 먼저 돌려야 한다. 기본 세트를 rr_dim_vocab 씨앗으로 지정하면 간극·벽 두께 결손이 함께 준다
- 풀리는 도메인(6) — xd · mech · disp · soc · pcb · rf
- 메커니즘 — interface.tolerance_stackup · interface.clearance_close · process.tolerance
- 질문 예 — 글래스-프레임 갭이 base 대비 얼마나 줄었나([d:] 인용) / 역할별 최소 벽과 역할 쌍 최소 간극이 리비전에서 어떻게 바뀌었나
- 선행 — MCAD-01 · MCAD-05 · MCAD-63
- 근거 — GW compare_dimension()(count 32, recordable 7도구, not_yet 5항) · SF/core/dimensions.py:104-231 · SF/core/data/dimension_sets.yaml:14-29 · SF/app/rest.py:1190, 1243 · HWAXMcpGateway/gateway.py:234-242 · HR/ir_builder.py:574-582 · PLAN:988 · DB rr_dim_defs·rr_dim_vocab 0행

### 리비전 비교

#### MCAD-56 · 리비전 변화(구조·치수·배치·재질·계면)

**부분 · P0**

- 돌려줘야 하는 것 — 심사 diff 이벤트 part.added·removed·replaced·moved{Δ[mm]}·rotated·resized·thickness_changed·material_changed, edge kind_changed·iface.gap_changed·band_area_changed·penetration_changed, comparability{tol_parity, unit_parity, coordinate_ok, app_version_parity}. StepForge compare_snapshots{yardstick, identity_shift_mm, moved[], reshaped{volume_before, volume_after, within_uncertainty}, connectors_delta}, compare_revisions{added, removed, renamed, moved, reshaped, material_changed}
- 지금 — rr_diff(IR 두 벌 — 브리프로 좌석에 전달) · compare_revisions·compare_snapshots·compare_part_view(좌석 열림) · match_parts_across·align_frames·explain_difference(좌석 닫힘)
- 빠진 것 — 행들의 상태가 갈렸다(have 2·partial 5). partial 로 정한다 — 구조 층만 지금 성립한다. 수치 변화는 tol_unknown 으로 빠지고(MCAD-16), moved·rotated 는 MCP 폴백에서 죽고(MCAD-58), volume·material 이 null 이며, 파트 대응에 위치 항이 없고(MCAD-02), 프레임 패리티 검사가 없고(MCAD-08), 엔진 빌드 차이를 못 본다(MCAD-05). 실제 리비전 쌍으로 검증된 적이 없다 — 유일한 diff 는 같은 스냅샷끼리다. 좌석은 risk_get_diff 를 부르지 못한다(러너가 넘기는 apps 가 step_forge·kooremapper 둘 — 일부 행의 '부를 수 있다' 는 틀렸다). StepForge 비교 결과는 [c:] 인용이 안 되고 패널 지정 도구에도 없다
- 풀리는 도메인(15) — xd · sim · cam · rel · soc · disp · mech · pcb · rf · passive · pwr · sh · mem · std · material
- 메커니즘 — interface.tied_loss · interface.interference · interface.clearance_close · mechanical.mass · material.supplier_change
- 질문 예 — base→target 에서 추가·삭제·교체·이동·변형된 파트는 무엇이고 이동량과 부피 변화는 얼마인가 / 두 리비전의 비교가 성립하나
- 선행 — MCAD-02 · MCAD-05 · MCAD-08 · MCAD-16 · MCAD-58 · MCAD-49
- 근거 — DB rr_diffs 1행(base=target 40b442da, events 0·params_excluded 6, tol_parity null·app_version_parity null)·rr_diff_events 0행 · HR/diff.py:209-300, 1355-1412 · HR/runner.py:191-199 · HR/adapters/registry.py:26-30 · AS:3104-3140 · HR/planner.py:255-275 · disc compare_snapshots 121칸

#### MCAD-57 · 지목 파트 반경 안 변화(공간 필터)

**도구는 있음 · 스냅샷 미수집 · P1**

- 돌려줘야 하는 것 — radius_mm, center(지목 파트 월드 무게중심), changes[]{kind(added|removed|moved|rotated|reshaped|relation_added|relation_removed|relation_class_changed|relation_gap_changed), part, distance_mm, before, after}, counts, blocked
- 지금 — what_changed_near(part, radius_mm)(좌석 닫힘, REST GET) · compare_snapshots·compare_revisions(판 전체, 좌석 열림) · 심사 diff 이벤트의 1홉 이웃 목록
- 빠진 것 — 심사 diff 에 공간 필터가 없다. what_changed_near 는 어댑터 미호출·좌석 닫힘이다. 스냅샷으로는 관계 행이 있는 이웃(0.5 mm 이내)까지만 따라갈 수 있다. 기준 파트를 정하려면 역할이 먼저다
- 풀리는 도메인(4) — xd · sh · pwr · rf
- 메커니즘 — interface.clearance_close · interface.tied_loss
- 질문 예 — 바뀐 파트 반경 N mm 안에서 관계가 달라진 이웃은 무엇인가 / 셀·방사체·음향 모듈 둘레에서 무엇이 추가·이동·변형됐나
- 선행 — MCAD-56 · MCAD-01
- 근거 — disc what_changed_near 85칸 · SF/app/rest.py:2224 · AS:2061-2105 · 행 검증 인용(GW risk_get_diff 스키마, HR/diff.py:472-480)

### 심사 스냅샷 수집

#### MCAD-58 · MCP 폴백 채널 동등성과 전량 벌크 읽기

**부분 · P0**

- 돌려줘야 하는 것 — 목록 도구의 offset|cursor·limit·total·truncated·omitted, MCP list_parts 의 world_bbox·world_center·material(수동 우선), get_project_meta 의 unit_system·tol_config, list_interfaces 의 path_a·path_b·tolerances, 한 세대 표식 generation, 또는 사람 개입이 반영된 단일 세대 IR 내보내기 한 호출
- 지금 — 잘림 플래그는 MCP·REST 양쪽이 낸다. REST /parts·/interfaces 는 limit 5000, MCP 는 MAX_ROWS 500. 폴백에 필요한 값은 게이트웨이 도구가 이미 준다
- 빠진 것 — MCP 채널은 노드가 500 을 넘으면 project_tree 가 nodes 를 빼고 어댑터가 mcad 를 통째로 버린다 — 실물은 647·919·940파트다(행 인용). 목록 도구에 offset 이 없다. REST 는 서비스 PAT 가 있어야 하고 라이브 호출 로그에 403 과 200 이 섞여 있다. 폴백에서 어댑터가 world 계열·unit_system·tol 을 읽지 않아 G6 차단·part.moved 불가가 된다 — 소스는 주는데 버린다. 사람이 고친 재질·역할이 한 세대로 오는 벌크가 없다
- 풀리는 도메인(15) — xd · sim · cam · rel · soc · disp · mech · pcb · rf · passive · pwr · sh · mem · std · material
- 메커니즘 — interface.cross_file_untrusted · new:process.data_comparability
- 질문 예 — 500파트·5,000계면을 넘는 실물 판을 빠짐없이 읽을 수 있는가 / REST 를 못 읽은 캡처에서도 이동·단위·잣대를 볼 수 있는가
- 근거 — HR/adapters/mcad.py:406-440, 784-794, 127-145 · SF/app/mcp_server.py:45 · SF/app/rest.py:570, 603 · GW list_parts 스키마(offset 없음)·실응답(world_bbox·world_center·truncated) · DB rr_snapshot_calls(REST 403 15건·200 20건)·rr_states(blocked 3/4)·rr_ir_nodes(dn 이 채널별로 다름)

#### MCAD-59 · 스냅샷용 사전계산 산출물(판 전체 형상 지표를 굽는 잡)

**부분 · P0**

- 돌려줘야 하는 것 — features{build, geo_key, params_hash, computed_at, complete(bool), per_definition[]{path, min_wall_mm, at_mm[3], obb_mm[3], ligament_mm}, per_pair[]{path_a, path_b, axis, axis_gap_min_mm, axis_gap_median_mm, overlap_mm2, gap_p10_mm, gap_median_mm, contact_ratio, penetrating_ratio, spacing_mm}, per_part[]{zone, layer, nearest[]{path, min_gap_mm, confirmed}}, fasteners[], stack[], skipped[]{path, reason}}
- 지금 — dimension 잡이 스칼라 측정을 영속하고 geo_key·build·stale 을 붙인다(일곱 도구의 칸만). measure 잡은 끝까지 재지만 결과가 job_status 에만 남는다. precheck·graph 잡은 산출물을 남긴다
- 빠진 것 — have_not_ingested 인 측정을 캡처 때 라이브 호출로 동결하는 길은 좁다 — 스냅샷 예산 180초, 게이트웨이 한 호출 120초이고 무거운 도구는 작업량 관문에서 partial 로 멈춘다. 판 전체 지표를 한 번 굽고 빌드·형상 키·완결 여부를 박은 산출물을 GET 한 번으로 읽는 잡 종류가 없다(종류 13). 읽기 계산의 REST 판 여럿이 POST 라 GET 전용 어댑터로 못 읽는다(clearance-field·stackup-profile·drop-check·part-index·slenderness-check·part-location·mass-estimate·tolerance-sweep·compare-dimension·compare-projects). 잡을 거는 것은 쓰기라 사람(반입 절차)이 건다
- 풀리는 도메인(9) — mech · disp · cam · sh · rf · pwr · soc · sim · material
- 메커니즘 — new:process.data_comparability
- 질문 예 — 벽 두께·축방향 간극·간극 분포·체결 치수를 180초 안에 판 전체에 대해 동결할 수 있는가 / 무거운 측정이 중간에 멈췄을 때 스냅샷은 그것을 '안 쟀다' 로 싣는가
- 선행 — MCAD-05 · MCAD-01
- 근거 — HR/config.py:166 · GW run_job 스키마(종류 13, measure·dimension) · GW glossary(tool='clearance_field') counterparts_unmeasured·job_call · SF/app/rest.py:1037-1103, 1190, 1243, 1747, 1973, 2174, 2188 · HR/adapters/base.py:88-114

#### MCAD-60 · 판의 처리 상태·미지 사유

**도구는 있음 · 스냅샷 미수집 · P1**

- 돌려줘야 하는 것 — list_unknowns{detected, counts{files_not_parsed, unmeasured_pairs, scoped, shell_uncompensated, structure_stale, missing_from_deck_mesh, without_geometry, excluded_from_deck, parts_without_material}, blocking[], caveats[]{code, count, of, why, do_next}}
- 지금 — list_unknowns(좌석 열림) · IR 비율 신호 sig:ratios.unconfirmed_ratio·material_null_ratio·auto_named_ratio
- 빠진 것 — 비율 신호는 수집되나 사유(안 잰 쌍·범위 검출·셸 미보정·구조 추론 없음·다른 빌드에서 검출·옛 저장값)는 어댑터 미호출이라 스냅샷만 보는 경로(evidence_only)에서는 안 보인다. 한 호출이면 되는 값이다
- 풀리는 도메인(3) — xd · mech · sim
- 메커니즘 — material.property_uncertain · interface.interference
- 질문 예 — 사람이 확정한 계면 비율, 재질 미기재 수, 안 잰 쌍·범위 검출 여부는 어떤가 / 이 판에 대해 답하지 말아야 할 질문은 무엇인가
- 근거 — GW list_unknowns(001a0dcc02ce36213eacd49) counts 9키·caveats 4건 · HR/state.py:382-385 · HR/adapters/mcad.py:17-19 · HWAXPortal/infra/pipeline/hwax-risk-review.js:11-12

#### MCAD-61 · 검출 잡 식별·범위(scope)와 범위 밖 표식

**부분 · P1**

- 돌려줘야 하는 것 — detect_job_id, finished_at, params{scope{match[], match_path[], bbox[6], mode}, tied_gap·clearance_gap…}, 검사한 쌍 수, 노드별 scope_out 플래그, list_unknowns.counts.scoped
- 지금 — heaxstep_forge_job_status(어댑터가 detect_job_id 가 있을 때만 부름)·heaxstep_forge_list_jobs·model_provenance.last_jobs(좌석 닫힘) · graph.json 의 scope
- 빠진 것 — detect_job_id 는 사람이 소스 카드에 적어야 하는데 라이브 스냅샷 4건 모두 null 이라 detect_absent 다 — 소스가 last_jobs 로 주는 값이다. scope_out 을 붙이는 생산자가 어댑터에 없어(소비 코드만) G5 가 무력하다 — 범위 밖 파트의 '계면 없음' 이 '떨어져 있음' 으로 읽힐 수 있다
- 풀리는 도메인(2) — xd · mech
- 메커니즘 — interface.clearance · interface.interference
- 질문 예 — 이 계면 표가 어느 검출 잡의 어느 범위에서 나왔는가, 범위 밖 파트는 무엇인가
- 선행 — MCAD-05
- 근거 — HR/adapters/mcad.py:342-362, 539 · HR 앱 코드 grep(scope_out) — state.py:252·diff.py·ir_builder.py 소비뿐, adapters 0건 · DB rr_snapshots(detect_job_id null, detect_absent 4/4) · GW run_job 스키마(detect scope) · disc model_provenance(last_jobs)

#### MCAD-62 · 형상 기반 실패모드 선별과 사람 판정 원장

**도구는 있음 · 스냅샷 미수집 · P1**

- 돌려줘야 하는 것 — findings[]{mode_id(tim_not_compressed|shield_can_contact_lost|thin_wall|hole_ligament|bend_formability|unconstrained_part|corner_drop_concentration), part, path, role, zone, indicators[]{tool, field, value, unit, worse_when}, zone_in_scope}, unknown[], 사람 판정 verdicts[]{part, mode_id, verdict, stale, changed}
- 지금 — risk_screen(좌석 닫힘, REST GET) · list_risk_verdicts·check_claim(좌석 열림) · set_risk_verdict(쓰기) · 사전 7모드
- 빠진 것 — 어댑터 미호출이라 StepForge 가 이미 가려낸 후보와 사람 판정이 심사에 전달되지 않는다. 사전에 문턱이 없어(전부 false) 판정 근거가 아니라 후보 목록으로만 써야 한다. 판 전체를 훑는 비싼 도구라 사람이 돌린 결과를 읽는 쪽이 맞다(지시에 따라 실호출하지 않았다)
- 풀리는 도메인(5) — mech · rel · cam · soc · pwr
- 메커니즘 — thermal.thermal_resistance · interface.tied_loss · mechanical.bending · mechanical.drop_stress · mechanical.rattle
- 질문 예 — 형상만으로 이미 가려낸 실패모드 후보와 사람이 낸 판정이 있는가
- 선행 — MCAD-01 · MCAD-27 · MCAD-34
- 근거 — GW list_tool_apps(heax-step_forge)에 risk_screen·set_risk_verdict·list_risk_verdicts · SF/core/data/failure_modes.yaml(modes 7키, 5-8행) · disc risk_screen 100칸 · SF/app/rest.py:949

#### MCAD-63 · 도구 읽기/쓰기 선언과 좌석 자유조회 통로

**부분 · P0**

- 돌려줘야 하는 것 — 도구별 annotations.readOnlyHint(bool)·side_effects(none|writes_record|runs_job), catalog.category(분석|수정|가시화|시스템), 좌석에 열 읽기 도구 목록
- 지금 — heaxstep_forge_system_capabilities.catalog.by_category 가 141종을 분석 98·수정 29·가시화 8·시스템 6 으로 가른다. 게이트웨이는 annotations 가 있으면 전달한다. 좌석 통로는 접두사 허용목록과 명시 6종, 예산은 좌석당 자유조회 1·도구 3회
- 빠진 것 — 141종 중 좌석에 열린 것은 32종, 닫힌 것은 109종이다 — 읽기 도구인데 이름이 접두사에 안 걸린다(clearance_field·axis_gap·measure_distance·nearest_parts·thickness_report·stackup_profile·fastener_report·leak_report·bend_profile·drop_check·resolve_materials·interface_summary·section_profile·what_changed_near·model_provenance·glossary 등). have_not_ingested 인 P0 항목이 스냅샷으로도 좌석 호출로도 닿지 않는다. MCP 워크플로 경로는 좌석 도구 0개다. StepForge 에 MCP annotations 가 없다 — 소스가 가진 분류를 쓰면 접두사 추측 없이 읽기만 열 수 있다. 비평의 P1 을 P0 로 올렸다(수집이 서기 전 P0 능력에 닿는 가장 싼 길). 예산이 3회라 통로만 열어서는 인용·diff 가 되지 않는다
- 풀리는 도메인(15) — xd · sim · cam · rel · soc · disp · mech · pcb · rf · passive · pwr · sh · mem · std · material
- 메커니즘 — new:process.evidence_integrity
- 질문 예 — 좌석이 부를 수 있는 도구가 정말 읽기만 하는지를 이름 추측 없이 알 수 있는가 / 좌석이 0.5 mm 밖 간극이나 실제 벽 두께를 실시간으로 조회할 수 있는가
- 근거 — AS:2061-2105, 644-655, 3104-3140 — GW 목록 141종에 적용해 열림 32(접두 26 + 명시 6)·닫힘 109 재계산 · GW heaxstep_forge_system_capabilities catalog · SF/app/mcp_server.py·catalog.py grep(readOnlyHint|annotations) 0건 · HWAXMcpGateway/gateway.py:556 · HR/planner.py:23-24

### 넣지 않은 것 — 16건

- 비평 제안 — 버튼 액추에이터–스위치 정렬·예압 측정을 독립 능력으로 — 이미 다른 항목이 덮는다. 편심·축방향 간극·측면 유격은 MCAD-26·MCAD-31·MCAD-25 로 재고, 빠진 것은 key·switch 역할 낱말뿐이라 MCAD-01 의 역할 목록에 넣었다. 스위치가 ECAD 에만 있으면 MCAD 쪽이 줄 수 있는 것이 아니다(좌표 정합 선행)
- 비평 제안 — 내측 코너 최소 반경(practitioner, P2)과 PMI 추출(practitioner) — 각각 coverage 렌즈의 같은 제안과 중복이다. MCAD-41(P1)·MCAD-30(P1) 하나씩으로 합쳤다
- 비평 제안 — 자세·척도 불변 기술자의 상태 have_not_ingested·P0 — 소스로 확인하니 snapshot_descriptors 의 norm 은 정의가 자기 좌표계 안에서 비스듬히 저장된 경우 불변이 아니다(독스트링 실측 상대차 0.104~0.987). 절대좌표로 구운 NX 판이 바로 그 경우라 수집만으로는 풀리지 않는다. partial·P1 로 고쳐 MCAD-04 에 실었다
- 비평 제안 — 외장(노출) 면 분류의 상태 partial — where_is 층·drop_check 첫 접지는 대용 지표일 뿐 노출 여부 칸은 어디에도 없다. missing 으로 고쳐 MCAD-13 에 실었다
- 비평 제안 — 형상 특징 대응 키의 상태 missing — compare_snapshots 가 connectors_delta·connectors_unmapped_b 로 동축 커넥터의 추가·삭제를 이미 센다(disc 칸표). partial 로 고쳐 MCAD-22 에 실었다
- 비평 서술 — app_version_parity 가 항상 참이다 — 라이브 diff 에서는 null 이다(DB rr_diffs.comparability_json). 결론(엔진 빌드 차이를 못 본다)은 맞아 MCAD-05 에 반영했고 수치만 고쳤다
- 비평 이의(mech-xd-48) — xd 계약 산출을 유지하려면 조립 순서 행이 P0 다 — 부분 수용. 조립 순서·삽입 방향은 STEP 에 없는 공정 문서라 MCAD 가 줄 수 없고(side other) 통제 어휘에도 해당 메커니즘이 없다. CAD 가 계산할 수 있는 넷(삽입 경로 간섭·공구 접근·분해 깊이·스크류 혼용)만 MCAD-33 에 P1 로 두고, 계약 문구를 좁히거나 공정 입력 채널을 여는 결정을 gap 에 적었다
- 비평 이의(mech-xd-46) — 지정번호·품번 키를 P0 로 — 부분 수용. 같은 이름이 134자리라 이 키로는 자리 단위 대응이 안 된다 — 인스턴스 구분은 MCAD-02(P0)가 지고 지정번호·품번 수집(MCAD-03)은 P1 로 둔다
- 비평 이의(material-sh-42·mech-xd-12) — 신규 메커니즘 코드가 통제 어휘 축을 벗어나고 같은 뜻이 갈린다 — MCAD 쪽이 제공할 수 있는 것이 아니다(어휘 개정은 심사 앱 자산 taxonomy.v1.json 의 일이다 — 38종·여섯 계열 확인). 이 카탈로그 안에서는 seal_path_continuity·fpcb_bend_radius 로 표기를 맞추고 sh.module_placement·sh.placement_change 같은 사건형 코드는 쓰지 않았다
- 비평 이의(disp-cam-39) — 카메라 모듈·팩 내부 사실을 세트 CAD 에 요구하는 행 — 수용. 모듈 내부(OIS 가동부·자석 바디·팩 내부·화각)는 공급사 사양(side other)으로 돌리고 MCAD 에는 봉투 대 주변 간극만 남겼다(MCAD-12·23·26·32 의 depends_on 과 gap). 화각 원뿔 간극 계산 자체는 CAD 계산이라 MCAD-32 로 남긴다
- 검증 행의 서술(pwr-45) — 좌석이 risk_get_diff 를 부를 수 있다 — 소스와 어긋난다. 러너가 좌석에 넘기는 apps 는 adapters/registry 의 step_forge·kooremapper 둘뿐이고(HR/runner.py:191-199, HR/adapters/registry.py:26-30) 자유조회는 그 앱으로 좁혀진다(AS:3104-3140). disp-cam-34 의 서술이 맞다
- 검증 행의 상태(mech-xd-41·sim-rel-std-79) — 리비전 변화 have — 비평 이의를 수용해 partial 로 내렸다(MCAD-56). 유일한 diff 가 같은 스냅샷끼리이고 이벤트 0·제외 6, 대응 사다리에 위치 항이 없으며 프레임 패리티 검사가 없다
- 검증 행의 상태(material-sh-43·mech-xd-13 의 build_cavity) — have_not_ingested — 비평 이의를 수용했다. build_cavity 는 StepForge 카탈로그 분류가 '수정' 인 잡이라 읽기가 아니다. '사람이 잡을 돌린 뒤 산출물을 읽는 통로가 없다' 로 고쳐 MCAD-47 을 partial 로 뒀다
- 검증 행의 상태(mech-xd-12·sim-rel-std-57) — 실링 경로 partial — 다시 확인하니 폐루프·위치별 폭·끊긴 구간을 내는 기능은 어디에도 없다(grep 0건). 쌍당 스칼라와 밀착 비율은 다른 항목(MCAD-14·27)이 지므로 경로 추출 자체는 missing 으로 정했다(MCAD-45)
- 비평 이의(rf-09) — 게이트웨이의 clearance_field 가 압착을 거꾸로 읽는 판일 수 있다 — dev 에 대해서는 기각. 게이트웨이 빌드가 cb0c578 이고 glossary 칸표에 penetrating_ratio·signed_* 가 있어 D-498 수정판이다. cae00 빌드는 확인하지 못했다. '모델링 상태(free|compressed)' 전제는 수용해 MCAD-18 에 실었다
- 비평 이의(sim-rel-std-40) — sim-rel-std 행 다수가 도구 이름만 있고 칸·단위가 없다 — 수용. 해당 행들은 같은 능력의 mech-xd·disp-cam 행과 합쳐 returns 에 칸·단위를 적었다(예 sim-rel-std-61 → MCAD-21, -55 → MCAD-46, -40 → MCAD-10)

## ECAD 쪽(ODB hub) — 48건

상태 분포 — 리포에 있음 · 미노출 27 · 부분 14 · 없음 4 · 계약에만 3. 우선순위 — P0 24 · P1 20 · P2 4.

### 보드·리비전 식별

#### ECAD-01 · 잡(보드) 식별 — 내용 해시·리비전 라벨·계보·보드 역할

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — 보드 1장당 1건. job_id(16 hex) · source_sha256(64 hex) · design_hash(포장과 무관한 내용 해시, 신설) · project · model · board_role(Main|Sub|S_AP…) · revision · predecessor_job_id(신설) · sibling_job_ids[] · odb_version · data_type(unit|array) · units_source(INCH|MM) · n_components(개, 미분류 포함) · n_nets(개) · uploaded_at(ISO) · parser_version. 식별 키는 job_id
- 지금 — 계약 안(odb_get_board 의 board_id·name·odb_version·source_hash·n_components·n_nets) · dev 리포 산출(meta.json 에 job_id·source_sha256·units·odb_version·data_type·revision 등, 개수는 캐시 길이) · cae00 문서 list_jobs·find_job(해시 칸 없음). dev REST JobOut 에는 source_sha256 이 빠져 있다
- 빠진 것 — 게이트웨이 도구가 없어 sources[ecad].source_hash 의 원천이 없다. predecessor_job_id·design_hash 는 어디에도 없다 — revision 은 사람이 고치는 자유 문자열이고 잡끼리 잇는 칸이 없다. 해시가 아카이브 바이트 기준이라 다시 묶으면 다른 잡이 된다. odb_version 은 포맷 버전이지 앱 버전이 아니다. 비평 제안의 P0 를 따른다 — 이것이 없으면 ECAD 소스를 동결할 수 없다
- 풀리는 도메인(9) — pcb · soc · mem · passive · pwr · rf · xd · sim · rel
- 메커니즘 — new:process.data_comparability · electrical.net · material.supplier_change
- 질문 예 — 이 보드 데이터는 어느 파일의 어느 리비전이며 직전 리비전은 어느 잡인가 / 같은 과제의 Main·Sub·인터포저 보드는 각각 어느 잡인가
- 선행 — 심사 앱: adapters/ecad.py 구현과 계약 개정
- 근거 — ODB/src/services/job_store.py:57,132-134,166-194,223-224 · ODB/api/schemas.py:13-25 · ODB/workspace/e67cbbdf95044b0a/meta.json(units INCH·odb_version 8.1·source_sha256 실측) · CONTRACT(odb_get_board 행) · PLAN:685,688 · REF §3·§4.2 · GW list_tool_apps(18앱·462도구, odb-hub unknown app)

#### ECAD-02 · 좌표·단위·회전·미러 규약의 칸별 선언

**계약에만 · P0**

- 돌려줘야 하는 것 — 응답마다 붙는 규약 블록. coord_unit(mm) · origin(step 원점, datum·origin[mm]) · rot{deg, 양의 방향(CCW|CW), 부품 rotation 과 핀 rotation 의 부호 일치 여부} · mirror{bottom 면 좌표 프레임, 미러 적용 주체} · thickness_unit(µm|mm) · pad_symbol_unit(mil|µm) · height{단위, 기준면, 공칭|최대} · 층 타입 어휘와 계약 5종 사상표 · units_source 와 환산 여부
- 지금 — 계약 일부(odb_get_board.units 한 칸) · dev 리포는 규약이 코드와 문서에만 있다(부품 rotation 은 캐시에서 무조건 부호 반전, Toeprint.rotation 은 미반전, mirror 는 소비자 처리, 좌표는 mm 로 정규화하되 심볼 단위와 유전체 두께는 원본 유지) · cae00 문서는 '항상 mm, 원점은 과제마다 다를 수 있다' 까지
- 빠진 것 — 규약을 값으로 내는 응답이 없다. 샘플은 원본이 INCH 인데 좌표는 mm, copper_data 두께는 inch 값 그대로다. 계약은 rot 부호·미러·높이 기준면을 정하지 않는다. 행은 P1 이었으나 P0 로 올린다(비평 수용) — 장축 각도·코너 볼·거리 계산과 ECAD↔MCAD 정합이 전부 이 선언 위에서만 검증되고 부호 뒤집힘은 오류 없이 지나간다
- 풀리는 도메인(11) — xd · pcb · soc · mem · passive · pwr · rf · mech · sh · cam · disp
- 메커니즘 — interface.cross_file_untrusted · new:process.data_comparability
- 질문 예 — ECAD 데이터의 단위·원점·회전 부호·면·미러 규약과 층 순서가 확정됐나 / 부품 회전각이 CW 양수인가 CCW 양수인가, bottom 면 좌표는 미러된 값인가
- 선행 — ECAD-01
- 근거 — ODB/src/services/data_service.py:389-452 · ODB/documents/ODB_RULES.md §3.3·§3.4·§4·§8.2 · CACHE copper_data.json·step_header.json·components_top.json(geom.units INCH) · CONTRACT 조건 3 · REF §3 · SEDMAP '계약 4도구 대조' · GW list_agents(domain='xd-ecad') xd-ecad-read

#### ECAD-03 · 소유·공개 범위와 호출자 신원 전달

**없음 · P2**

- 돌려줘야 하는 것 — 잡별 owner(계정) · visibility(private|org) · 호출마다 전달된 caller 와 감사 행(caller, tool, job_id, 시각)
- 지금 — 계약 조건 2 에 문장만 있다 · dev 리포는 무인증이고 X-User 자기 선언 이름만 받는다 · cae00 문서는 서비스 토큰 하나로 통째 인증, uploaded_by 전부 anonymous
- 빠진 것 — 호출자별 시야가 없어 미공개 보드가 소스 등록 한 번으로 모든 좌석에 닿는다. 제안은 P1 이었으나 P2 로 둔다 — 좌석이 말할 내용이 아니라 누가 볼 수 있는지를 바꾼다(배포 승인에서는 차단 요건일 수 있다). 제안의 '잡 삭제 REST 가 열려 있다' 는 틀렸다 — 관리자 비밀번호 헤더로 막혀 있다
- 풀리는 도메인(6) — pcb · soc · mem · passive · pwr · rf
- 메커니즘 — new:process.evidence_integrity
- 질문 예 — 이 보드 잡을 볼 자격이 있는 사람만 스냅샷과 좌석 조회로 그 내용을 보게 되는가
- 선행 — ECAD-01
- 근거 — ODB/api/deps.py:34-43 · ODB/api/routers/jobs.py:139-150 · CONTRACT 조건 2 · REF §1·§3

### 스택업·동박

#### ECAD-04 · 스택업 층 표 — 층 순서·종류·층별 두께·동박 무게

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — layers[]{key(층 이름·역할 기반 안정 키), idx(매트릭스 row), name, type_raw, type(계약 5종 사상값|null), add_type(COVERLAY|PG_FLEX|STIFFENER…), thickness_um, thickness_source, copper_weight_oz, polarity}. 도전층·유전층·솔더레지스트를 위에서 아래로 빠짐없이
- 지금 — 계약 안(odb_get_stackup 의 idx·name·type·thickness·copper_weight) · dev 리포 산출(매트릭스 row·name·type·add_type 와 copper_data — SIGNAL 의 .copper_weight÷1000, DIELECTRIC 의 .layer_dielectric) · cae00 문서 get_board_layers·check_job_stackup. dev REST /layers 는 name·type 만
- 빠진 것 — 두께가 SIGNAL·DIELECTRIC 뿐이라 POWER_GROUND(샘플 plane_4·flex_5·flex_6)와 솔더레지스트가 빠지고 값이 원본 단위(샘플 inch) 그대로다. 층 타입이 계약 5종과 다르다(샘플 10종). 심사 IR 층 키가 ecad:layer:<idx> 라 층이 끼면 뒤 층이 전부 다른 노드가 된다(비평 수용, 심사 쪽 변경). 행 상태가 contract_only·have_not_ingested·partial 로 갈렸으나 리포가 층 순서·두께를 보관하므로 이 상태로 정했다
- 풀리는 도메인(9) — pcb · soc · mem · sim · rel · material · pwr · rf · disp
- 메커니즘 — process.warpage · thermal.cte_mismatch · thermal.solder_fatigue · electrical.si_pi · new:thermal.charging_heat · new:electrical.rf_path_loss
- 질문 예 — 스택업이 두께 중심면 기준으로 대칭인가 — 어긋나는 층은 어디인가 / 충전 경로가 지나는 층의 동박 두께는 얼마인가 / 층별 두께·자재·동박 무게
- 선행 — ECAD-01 · ECAD-02
- 근거 — ODB/src/services/data_service.py:356-370 · ODB/src/parsers/matrix_parser.py:43-51 · ODB/src/models.py:154-171 · ODB/src/services/viewer_service.py:50-61 · CACHE matrix_layers.json(43행·타입 10종)·copper_data.json(16층, POWER_GROUND 없음) · CONTRACT · PLAN:719 · REF §3·§4.7

#### ECAD-05 · 보드 총두께·신호층 수·표준 스택업 판정

**계약에만 · P0**

- 돌려줘야 하는 것 — total_thickness_mm · thickness_source(.board_thickness|층 합|표준 대조) · layer_count_matrix · signal_layer_count · stackup_verdict(standard|ambiguous|non_standard|unknown) · chosen_stackup_id · chosen_by_user · suggestions[]
- 지금 — 계약 안(odb_get_board.thickness·layer_count, 예약 치수 ecad_stackup_total) — 판정은 계약 밖 · dev 리포 없음(misc/attrlist 를 읽는 parse_attrlist 가 정의뿐이고 호출처 0건, 표준 스택업 코드 0건) · cae00 문서 get_board_layers·check_job_stackup·match_stackup·list_stackups(53종, 응답 표본 있음)
- 빠진 것 — dev 에서는 총두께가 나오지 않는다 — 층 합은 POWER_GROUND 누락과 단위 미정규화로 못 쓴다. layer_count 정의(매트릭스 행 수 대 신호층 수)를 정해야 한다. cae00 문서가 'ODB 내부 두께는 틀린 경우가 잦다' 고 적어 verdict 가 필요한데 계약·rr_ir 에 자리가 없다
- 풀리는 도메인(5) — pcb · soc · mem · sim · rel
- 메커니즘 — process.warpage · mechanical.bending · thermal.solder_fatigue · thermal.cte_mismatch
- 질문 예 — 보드 총두께와 신호층 수가 base→target 에서 바뀌었는가, 사내 표준 스택업에 있는 조합인가 / AP 실장부 보드의 총두께·층수·표준 스택업 여부는 어떤가
- 선행 — ECAD-04
- 근거 — ODB/src/parsers/misc_parser.py:30-33(호출처 grep 0건) · ODB/src·api grep 'board_thickness|match_stackup'(0건) · CONTRACT · PLAN:874,988 · REF §3·§4.7·§4.8·§4.17 · GW pcb_warpage_surrogate 스키마(board_thickness_mm 필수)

#### ECAD-06 · 층 자재 구분·등급·유전 특성

**계약에만 · P1**

- 돌려줘야 하는 것 — layers[]{key, material_class(CU|PPG|CCL|RCC|SR|PI), material_grade(제조사·품번|null), material_source(odb|stackup.xml|standard_stackup|user), Dk, Df, target_impedance_ohm}
- 지금 — 계약 안(material 한 칸) — 등급·Dk·Df 는 밖 · dev 리포는 매트릭스 dielectric_name 칸(샘플은 전부 빈 값)과 stackup.xml 원문 dict 만 둔다(읽는 코드 없음, 샘플에 파일 없음) · cae00 문서 check_job_stackup 의 자재 구분 5종(표준 라이브러리 대조값)
- 빠진 것 — 자재 등급과 Dk·Df 는 어디서도 확인되지 않았다(stackup.xml 내용은 표본이 없어 unverified). cae00 의 자재 구분은 ODB 원본이 아니라 표준 대조로 채운 값이라 출처 칸 없이 측정 등급으로 인용하면 안 된다. 물성(E·CTE·Tg)은 물성 DB 몫이다
- 풀리는 도메인(5) — material · pcb · rf · soc · mem
- 메커니즘 — thermal.cte_mismatch · process.warpage · material.supplier_change · material.property_uncertain · new:electrical.rf_path_loss
- 질문 예 — 적층 자재(CCL·PPG 등급)가 리비전에서 바뀌었는가 / RF 선로의 기준면 간격과 유전체 값은 얼마인가
- 선행 — ECAD-04 · other: 물성 DB(자재 등급 → E·CTE·Tg)
- 근거 — ODB/src/parsers/matrix_parser.py:50-51 · ODB/src/parsers/stackup_parser.py:10-28,91-124 · ODB/src/services/data_service.py:379-387 · CACHE matrix_layers.json(dielectric_name 빈 값, stackup.json 없음) · REF §3·§4.8

#### ECAD-07 · 층별·격자 동박률

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — layers[]{layer_name, type, total_ratio(0~1), grid{n_rows, n_cols, x0·y0·cell_w·cell_h[mm], ratios[][]}, thickness_um} · params{method} · result_id · completed_at. 도전층 전체(SIGNAL + POWER_GROUND)
- 지금 — 계약 밖 · dev 리포 산출(copper_service.run_report 가 SIGNAL 층마다 total_ratio 와 n×n 구간 비율을 계산) — dev REST 는 내부 키를 걷어 내고 층 수·평균·HTML 만 준다 · cae00 문서 run_analysis(copper) 뒤 get_copper_result(성공 표본 없음). ODB 자체 규격서에 odb_copper_ratio 계획(미구현)
- 빠진 것 — 대상이 SIGNAL 층뿐이라 플레인 층이 빠진다. 계산이 결과를 덮어쓰는 실행형이라 읽기 전용 어댑터와 좌석이 부를 수 없다 — 캐시 생성 때 미리 계산하거나 조회를 분리해야 한다. 격자 원점·셀 크기가 없어 구간을 refdes 와 이을 수 없다. 계약·rr_ir 에 자리가 없다
- 풀리는 도메인(5) — pcb · soc · mem · sim · rel
- 메커니즘 — process.warpage · process.solder · new:process.package_warpage
- 질문 예 — 층별 잔동률(%)과 리비전에서 가장 크게 변한 층은 어디인가 / AP 풋프린트 아래 구간의 층별 동박률은 얼마인가
- 선행 — ECAD-04 · ECAD-43
- 근거 — ODB/src/services/copper_service.py:57-146(77-80) · ODB/api/routers/copper.py:37-45 · ODB/src/visualizer/copper_vector.py:616,646 · ODB/documents/MCP_INTEGRATION.md §4.1 · REF §2·§4.13 · SEDMAP '워피지 입력 5개'

#### ECAD-08 · 동박 불균형·스택업 비대칭 지수

**부분 · P1**

- 돌려줘야 하는 것 — copper_imbalance_pct(정의 명시) · stackup_asymmetry(0~1, 정의 명시) · mismatched_pairs[]{upper_key, lower_key, Δthickness_um, material 차이} · 지정 풋프린트 하부 국부 동박률 % · 리비전 간 Δtotal_ratio by layer
- 지금 — 계약 밖 · dev 리포에는 원자료만 있다(ECAD-04 층 두께, ECAD-07 층별 동박률) · cae00 문서도 산식 없음. GW pcb_warpage_surrogate 가 두 값을 필수 입력으로 받지만 정의를 주지 않는다. 적층 결합 지수 커널(Laminate Analyzer)은 backend_down
- 빠진 것 — 빠진 것은 산식 정의와 어긋난 층 쌍 계산이다. 층별 동박률이 rr_ir 에 실리면 Δ 는 심사 diff 가 맡을 수 있다. 대리모델이 합성 데이터 데모라고 스스로 밝히므로 지수가 생겨도 근거 등급은 낮다
- 풀리는 도메인(4) — pcb · soc · mem · sim
- 메커니즘 — process.warpage · thermal.cte_mismatch
- 질문 예 — 상·하 절반의 동박 불균형(%)은 얼마인가 / 스택업 비대칭 지수와 어긋난 층 쌍은 무엇인가
- 선행 — ECAD-04 · ECAD-07
- 근거 — SEDMAP '워피지 입력 5개'(산식 미정) · GW pcb_warpage_surrogate 스키마·설명 · GW list_tool_apps(heax-laminate_analyzer_mcp backend_down) · ODB/src/comparator/comparators(파일 2개)

### 부품·패키지

#### ECAD-09 · 부품 배치 목록(보드 전체 일괄)과 완결성 선언

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — components[]{refdes, part_number, footprint(pkg_name), side, x_mm, y_mm(스텝 원점), rot_deg, mirror, pin_count, category(8범주, Unknown 포함), mounted, odb_comp_id} + total_components(미분류 포함) · returned · excluded_unknown_n · has_more · sort_key(결정론적 정렬) · generation. 한 호출 또는 한 파일로 전량
- 지금 — 계약 안(odb_list_components 의 refdes·part_number·footprint·side·x·y·rot·pin_count) — category·mirror·완결성 칸은 밖 · dev 리포 산출(POST /jobs/{id}/extract 의 parts.json 과 GET /jobs/{id}/cache.zip 이 좌표·회전·미러를 준다, REST /components 는 refdes·part·category·side 넷뿐) · cae00 문서 list_parts(좌표 없음)·get_part_detail(부품당 1호출)
- 빠진 것 — parts.json 은 Unknown 분류를 뺀다 — 샘플에 분류기를 그대로 적용하면 692개 중 388개가 Unknown 이다(스크래치 재현). ANT 접점·BOTHHOLE·TP·다이오드·서미스터가 여기 든다. pkg_name 이 parts.json 에 없다. cae00 실물은 좌표가 부품당 1호출이라 1,500개 보드에서 예산을 넘는다. 계약에는 총 상한 2000 만 있고 정렬 규칙이 없다. cae00 의 list_parts 는 StepForge 의 list_parts 와 이름이 겹친다(충돌 시 게이트웨이가 앱 접두를 붙인다, cae00 결과 unverified). 행 상태가 넷으로 갈렸으나 리포가 값을 이미 낸다
- 풀리는 도메인(14) — pcb · soc · mem · passive · pwr · rf · xd · mech · sim · rel · std · sh · cam · disp
- 메커니즘 — mechanical.drop_stress · thermal.solder_fatigue · thermal.thermal_shock · thermal.hotspot · new:mechanical.board_strain · new:mechanical.mlcc_flex_crack · new:electrical.desense · new:interface.connector_retention · new:acoustic.port_alignment · new:sensor.mounting_stress_offset · new:process.data_comparability
- 질문 예 — AP 가 어느 refdes 이고 어느 면·좌표·회전에 놓였는가 / 2012 이상 MLCC·인덕터는 몇 개이고 어느 면·좌표에 있는가 / 패널 FPCB 가 물리는 BTB 커넥터는 어디에 있는가 / 받은 부품 목록이 보드의 전부인가, 분류에서 빠지거나 잘린 것이 있는가
- 선행 — ECAD-01 · ECAD-02 · 심사 앱: adapters/ecad.py 구현과 계약 개정
- 근거 — ODB/src/services/extract_service.py:32-34,56-73,125-138 · ODB/api/routers/jobs.py:184-209 · ODB/src/services/viewer_service.py:310-330 · ODB/api/schemas.py:134-138 · ODB/src/checklist/component_classifier.py:29-76 · CACHE components_top.json(610)·components_bot.json(82) · RISK/backend/app/adapters/ecad_stub.py:13-41 · RISK/backend/app/planner.py:26,143-145 · REF §2·§4.4~§4.6 · GW list_tool_apps(app='heax-step_forge') list_parts

#### ECAD-10 · 부품 높이(최대·최소)와 출처

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — components[]{refdes, height_max_mm, height_min_mm, height_source(property COMP_HEIGHT_MAX/MIN|attribute .comp_height|absent), height_basis(라이브러리 공칭 — 스탠드오프·공차 미포함 여부), stacked(PoP 포함 여부|unknown)} + missing_height_n
- 지금 — 계약 안(height|null 한 칸 — 최대·최소·출처는 밖) · dev 리포 산출(체적 서비스가 properties 의 COMP_HEIGHT_MAX·MIN 평균을 부품별 height_mean_mm 로 낸다, 파서는 attributes .comp_height 도 보관 — 샘플 top 609/610·bottom 82/82) · cae00 문서 list_parts·get_part_detail 에 height 없음
- 빠진 것 — 최대 높이를 따로 내는 응답이 없다. .comp_height 속성은 읽는 코드가 없고 단위 정규화도 안 된다(샘플 값은 inch, properties 쪽 키는 0건이라 체적 계산에서는 전부 높이 미상). 값은 라이브러리 공칭이라 Z 간극 소견은 데이터시트 최대 높이를 전제로 적어야 한다(비평 수용). 행 상태가 contract_only 5·in_repo_not_exposed 1 로 갈렸으나 리포가 값을 읽어 REST 결과로 낸다
- 풀리는 도메인(9) — mech · xd · soc · pcb · pwr · rf · sh · disp · cam
- 메커니즘 — interface.clearance · interface.clearance_close · interface.tolerance_stackup · new:mechanical.shield_can_clearance · new:mechanical.battery_puncture · new:optical.crosstalk_airgap
- 질문 예 — 쉴드캔 상면 내측과 캔 안 최고 부품 상면 사이 간극은 얼마인가 / AP 상면에서 쉴드캔 천장까지 Z 간극과 공차 최악값은 얼마인가 / 셀 면을 마주 보는 PCB 실장 부품의 최대 높이는 얼마인가
- 선행 — ECAD-09 · ECAD-02 · join: 보드 좌표계→어셈블리 좌표계 변환
- 근거 — ODB/src/services/volume_service.py:8-11,40-75 · ODB/api/routers/volume.py:35 · ODB/src grep comp_height(volume_service.py 뿐) · CACHE components_top.json·components_bot.json(.comp_height 실측) · CONTRACT · REF §4.5·§4.6·§4.11

#### ECAD-11 · 패키지 기하 — 바디 치수·피치·볼 수·핀 좌표·코너 볼·DNP

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — refdes 별 {pkg_name, body_x_mm·body_y_mm(로컬 축 규약 명시), pitch_mm, pin_count, is_bga, pins[]{name, x_mm, y_mm(보드 좌표)} 전량(또는 pins_truncated·pin_cap 명시), corner_pins[4], outermost_pins[], DNP_max_mm, empty_center}
- 지금 — 계약 일부(footprint·pin_count) · dev 리포 산출(EDA PKG 의 pitch·bbox·pins, is_bga_type·find_outermost_pin_indices·has_empty_center, parts.json 의 핀 좌표는 상한 없음 — 샘플 BGA440 pitch 0.5 mm·440핀) · cae00 문서 list_parts(pkg_width·pkg_length)·get_part_detail(핀 최대 200개)
- 빠진 것 — parts.json 에 pitch·pkg_name·바디 치수가 실리지 않는다(파싱은 한다). 코너 볼과 DNP 는 계산이 없다 — 핀 좌표에서 결정론적으로 나오는 새 계산이다. cae00 실물은 200핀에서 잘려 AP 급 코너 볼이 빠질 수 있다. 바디 폭·길이의 축 규약이 없다
- 풀리는 도메인(6) — soc · mem · sim · rel · mech · pcb
- 메커니즘 — thermal.solder_fatigue · thermal.cte_mismatch · thermal.thermal_shock · new:mechanical.board_strain · mechanical.drop_stress
- 질문 예 — AP 패키지의 바디 크기·볼 피치·볼 수·코너 볼 좌표와 DNP 는 얼마인가 / UFS/uMCP 패키지의 코너 볼 좌표와 DNP 는 얼마인가
- 선행 — ECAD-09 · ECAD-02
- 근거 — ODB/src/parsers/eda_parser.py:203-243 · ODB/src/models.py:419-441 · ODB/src/checklist/component_classifier.py:297-336 · ODB/src/checklist/geometry_utils/overlap.py:202,233,1054 · ODB/src/services/extract_service.py:37-53 · CACHE eda_data.json(패키지 186, pitch 0 아닌 것 111) · REF §4.6 · GW sed_sample_from_odb 설명

#### ECAD-12 · 부품 역할 표 — AP·메모리·PMIC·센서·RF·보호소자

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — roles[]{refdes, role(AP|CP|DRAM|MCP|UFS|PMIC|charger|charge_pump|OVP|PA|LNA|RF_filter|RF_switch|tuner|XO|hall|axis_sensor|baro|mic|LED|connector|RF_receptacle|antenna_contact|TVS|NTC…), basis(reference_csv|refdes 접두|FNC·SSHEET|TYPE·DESCRIPTION|user), role_source, is_bga}. 사람이 지정한 refdes→role 을 받는 자리 포함
- 지금 — 계약 밖 · dev 리포 산출(분류 8범주와 finder — find_ap_memory·find_pmics·find_oscillators·find_mics·find_rf_components·find_filters·find_antennas·find_leds·find_bga_ics, 홀 IC·축 센서는 참조 CSV) — 전부 규칙 내부용 · cae00 문서는 category 와 device_type 뿐이고 '역할은 사람이 refdes 를 지정' 이라 적는다
- 빠진 것 — finder 결과를 돌려주는 응답이 없다. 어휘에 차저·PA·LNA·튜너·UFS 단품·TVS·서미스터·기압 센서가 없다(샘플의 서미스터 R154·R155 는 DESCRIPTION 으로만 식별). dev 참조 CSV 가 내장 샘플이라 AP·메모리·홀 IC 판정이 실목록 기준이 아니다(ECAD-44). 소비전력은 ODB 에 없다
- 풀리는 도메인(10) — soc · mem · pwr · rf · sh · cam · disp · sim · passive · pcb
- 메커니즘 — thermal.hotspot · thermal.thermal_shock · thermal.solder_fatigue · new:electrical.desense · new:thermal.charging_heat · new:sensor.thermal_drift · new:magnetic.interference · new:thermal.sensor_placement · new:electrical.esd_path
- 질문 예 — 이 보드에서 AP(및 CP·모뎀)가 어느 refdes 인가 / 차저 IC·차지펌프·PMIC 같은 전원 발열 부품은 보드 어디에 있는가 / 홀 IC·자이로·지자기 센서는 보드 어디에 있는가
- 선행 — ECAD-09 · ECAD-44 · other: 부품 소비전력
- 근거 — ODB/src/checklist/component_classifier.py:18-76,83-127,194-291,297-365 · ODB/src/checklist/reference_loader.py:23-111 · ODB/src/checklist/rules/ckl_01_007.py:24 · CACHE components_top.json(TYPE 9종, DEVICE_TYPE 0/610, R154·R155) · REF §5·§6

#### ECAD-13 · 부품 속성·BOM — 품번·MPN·벤더·값·정격·실장 여부

**리포에 있음 · 미노출 · P1**

- 돌려줘야 하는 것 — components[]{refdes, part_number, bom{cpn, ipn, pkg, description, vendors[]{vendor, mpns[]{mpn, chosen, qualify_status}}}, vpl_vendor, vpl_mpn, value, volt_rating_V, tolerance, power_rating, description, type, mounted, properties_raw{}} + 속성 키 사전
- 지금 — 계약 일부(part_number·value) · dev 리포 산출(BomData 와 PRP 속성 전부, VPL_VND·VPL_MPN — parts.json 은 properties 를 통째로 싣되 bom_data 는 싣지 않는다. 샘플 top 610개 중 VALUE 290·VOLT 287·TOLER 396·VPL 534·MOUNTED 86) · cae00 문서 표본에는 part_name·device_type·type 까지만
- 빠진 것 — MPN·벤더·정격을 주는 도구가 없다. 속성 키 이름이 원천마다 다르다(같은 샘플에 VOLT 와 VOLTAGE 가 섞여 있다). Unknown 부품은 parts.json 에서 빠져 저항·다이오드·서미스터 속성이 안 나간다
- 풀리는 도메인(8) — passive · pwr · xd · rel · mem · soc · material · rf
- 메커니즘 — material.supplier_change · new:electrical.dc_bias_derating · electrical.si_pi · new:mechanical.mlcc_flex_crack · process.solder
- 질문 예 — 전원 레일 MLCC 의 정격전압·케이스 크기는 무엇인가 / 대책품인가 — 부품번호·벤더·MPN 은 무엇인가 / 실장 안 함(MOUNTED) 소자와 옵션 풋프린트는 어디인가
- 선행 — ECAD-09
- 근거 — ODB/src/parsers/component_parser.py:78-130 · ODB/src/models.py:485-492 · ODB/src/services/extract_service.py:56-73 · CACHE components_top.json·components_bot.json(속성 키 빈도 실측) · CONTRACT · REF §4.5·§4.6

#### ECAD-14 · 소자 크기 코드·장축 각도(실장 방향)

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — components[]{refdes, size_code(metric LLWW), size_basis(DESCRIPTION|참조표|패키지 bbox), major_axis_angle_deg([0,180), 보드 X 기준), orientation(Horizontal|Vertical|Square|Unknown)}
- 지금 — 계약 밖 · dev 리포 산출(get_component_size, get_major_axis_angle, get_component_orientation) — 규칙 내부용 · cae00 문서는 관리부품의 size 만, 각도 칸 없음
- 빠진 것 — 임의 소자에 대한 응답이 없다. 각도는 보드 X·Y 기준일 뿐 굽힘 주방향 기준이 아니다 — 굽힘축은 MCAD·해석 쪽에서 와야 한다
- 풀리는 도메인(3) — passive · rel · pcb
- 메커니즘 — new:mechanical.mlcc_flex_crack · mechanical.bending · mechanical.drop_stress
- 질문 예 — MLCC 장축이 보드 굽힘 주방향과 나란한 소자는 어느 것인가 / 2012(metric) 이상 MLCC·인덕터는 몇 개인가
- 선행 — ECAD-09 · ECAD-02 · mcad·sim: 보드 굽힘 주방향
- 근거 — ODB/src/checklist/geometry_utils/size.py:49-97 · ODB/src/checklist/geometry_utils/orientation.py:37-128 · REF §4.6·§4.9

#### ECAD-15 · 인터포저 유무·면적비

**리포에 있음 · 미노출 · P1**

- 돌려줘야 하는 것 — 면별 {count, pcb_area_mm2, interposer_area_mm2, ratio_pct, items[]{refdes, area_mm2}} + AP 와 상대 패키지가 같은 잡(같은 좌표계)인지
- 지금 — 계약 밖 · dev 리포 산출(interposer_service, 판정은 refdes 접두 INP|INT) — dev REST 는 실행형 POST · cae00 문서 get_interposer_result(응답 표본 있음)
- 빠진 것 — 게이트웨이 도구와 계약 자리가 없다. AP 와 상대 패키지가 다른 잡에 있을 수 있는데 잡 간 결속 정보가 없다(ECAD-01)
- 풀리는 도메인(3) — soc · mem · sim
- 메커니즘 — thermal.thermal_shock · process.warpage
- 질문 예 — AP 가 인터포저 보드에 있는가, 인터포저 면적비는 얼마이고 AP 와 상대 패키지가 같은 보드에 있는가
- 선행 — ECAD-09 · ECAD-01
- 근거 — ODB/src/services/interposer_service.py:94-148 · ODB/api/routers/interposer.py:35 · ODB/src/checklist/component_classifier.py:129-131 · REF §4.12 · GW sed_sample_from_odb 설명

#### ECAD-16 · 부품·보드 체적과 질량

**리포에 있음 · 미노출 · P2**

- 돌려줘야 하는 것 — items[]{refdes, area_mm2, volume_mm3, mass_g(밀도 출처 명시)} · 면별 합계·missing_height_n · board{outline_area_mm2, thickness_mm, volume_mm3, mass_g} · scope(unit|array)
- 지금 — 계약 밖 · dev 리포 산출(volume_service 가 실장된 모든 부품의 면적×평균 높이 체적을 낸다 — 질량·보드 체적은 dev 에 없다) · cae00 문서 get_volume_result(보드 체적·질량, 상위 10개)
- 빠진 것 — dev 리포에 질량·밀도가 없다(grep 0건). 질량 대 패드 면적 비 같은 2차 지표는 ECAD-10·ECAD-22 에서 유도된다. 높이 속성이 없는 보드는 체적이 전부 비는데 합계가 0 으로만 보인다
- 풀리는 도메인(4) — pcb · sim · mech · passive
- 메커니즘 — mechanical.mass · mechanical.drop_stress · process.solder
- 질문 예 — 보드 조립체와 큰 부품의 질량이 얼마이고 해석 모델·질량 추정과 맞는가
- 선행 — ECAD-10 · ECAD-09
- 근거 — ODB/src/services/volume_service.py:1-11,62-75,135-188 · ODB/src·api grep 'mass|density'(코드 0건) · REF §4.11

### 넷·전류 경로

#### ECAD-17 · 보드 전체 넷 목록 — 이름·핀 수·경유 층·식별 안정성

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — nets[]{net_name, pin_count, layers[], via_count, kind(GND|PWR|SIG|NC, 근거), net_class|null, auto_named(bool), pseudo(bool, $NONE$), pin_set_hash(정렬한 refdes.pin 의 sha1)} · total · 결정론적 정렬의 페이지
- 지금 — 계약 안(odb_list_nets 의 net_name·pin_count·layers[]·net_class) · dev 리포 산출(eda.nets 의 이름과 서브넷 VIA|TRC|PLN|TOP, 넷→층 역색인 — 샘플 677넷) — dev REST 는 층을 인자로 줘야 그 층의 넷 이름만 준다 · cae00 문서에도 넷 목록 도구가 없다
- 빠진 것 — 넷 목록과 넷별 핀 수를 내는 응답이 어디에도 없다(세는 함수만 없다). net_class 는 리포에 칸이 없고 샘플 넷 속성이 677개 전부 비어 있다. 샘플에 $NONE$ 1개와 $1N145 꼴 4개가 있다 — 무명 넷은 재출력마다 번호가 달라져 가짜 변경이 뜨고 $NONE$ 은 미연결 핀을 한 노드에 묶는다(심사 IR 키가 ecad:net:<net_name>). 넷 전압·전류는 ODB++ 에 없다. 행 넷 모두 contract_only 였으나 리포가 값을 보관한다
- 풀리는 도메인(8) — pwr · rf · mem · soc · sim · cam · disp · passive
- 메커니즘 — electrical.net · electrical.si_pi · electrical.emi · new:electrical.desense
- 질문 예 — 전원 레일 넷(VBAT·VBUS·VDD_x)의 목록과 각 넷에 물린 부품은 무엇인가 / 쉴드캔 경계를 넘거나 안테나 영역을 지나는 RF·고속 넷은 무엇인가 / 이름 없는 넷이 리비전 사이에서 '넷 변경' 으로 잘못 뜨지 않는가
- 선행 — ECAD-01
- 근거 — ODB/src/parsers/eda_parser.py:60-87,157-200 · ODB/src/models.py:380-408 · ODB/src/visualizer/net_filter.py:13-40 · ODB/api/routers/viewer.py:28-33 · ODB/src·api grep 'net_class|impedance|differential'(코드 0건) · CACHE eda_data.json(nets 677, 속성 0)·netlist.json · CONTRACT · PLAN:719 · SEDMAP '계약 4도구 대조'

#### ECAD-18 · 핀 표 — 핀별 넷·좌표·패드 심볼과 넷→핀 역조회

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — pins[]{refdes, pin_name, pin_num, net_name, x_mm, y_mm, side, pad_symbol, is_corner, is_outermost} 전량 + 역조회 net_name → pins[]
- 지금 — 계약 밖(net 엣지가 부품→넷 1건이라 핀이 사라진다) · dev 리포 산출(Toeprint 와 FID 로 해석한 패드 심볼, parts.json 의 pins[]{pin_num, name, net, pad, x, y} — 샘플 toeprint 2,447개 전부 넷 보유) · cae00 문서 get_part_detail.pins[](부품당 1호출, 최대 200핀)
- 빠진 것 — 넷에서 핀을 되짚는 조회가 없다(TOP 서브넷의 comp_num·toep_num 이 파싱돼 있어 뒤집기만 하면 된다). Unknown 부품의 핀이 빠져 급전 넷·보호 경로의 한쪽 끝이 안 보인다. 핀 번호 매칭이 ±1 휴리스틱이다. P0 질문(핫루프·메모리 볼맵·배터리 커넥터 핀당 전류)에 필요해 계약의 '넷당 1건' 을 깨야 한다
- 풀리는 도메인(7) — pwr · rf · mem · soc · passive · mech · std
- 메커니즘 — electrical.net · electrical.si_pi · electrical.emi · new:interface.connector_retention · new:electrical.antenna_detune · electrical.pad_lift
- 질문 예 — 배터리 커넥터의 VBAT·GND 핀 수는 얼마인가 / 안테나 접지·급전 넷에 튜너·스위치·매칭 소자가 어떻게 물려 있는가 / 메모리 볼맵(핀별 넷)
- 선행 — ECAD-09 · ECAD-17
- 근거 — ODB/src/models.py:454-482 · ODB/src/services/extract_service.py:37-53 · ODB/src/parsers/eda_parser.py:169-185 · ODB/documents/ODB_RULES.md §7.4·§14 · CACHE components_top/bot.json(toeprints 2,243+204) · CONTRACT('넷 당 1건') · REF §4.6

#### ECAD-19 · 넷 배선 기하 집계 — 층별 길이·최소 폭·비아 수·플레인 면적

**부분 · P0**

- 돌려줘야 하는 것 — net_name 별 {segments_by_layer[]{layer, length_mm, min_width_um, max_width_um}, total_length_mm, via_count, via_spans[]{start_layer, end_layer, n}, plane_area_mm2 by layer, bbox_mm[4], crosses(region)→bool}. 넷 그룹 질의 가능
- 지금 — 계약 일부(layers[] 만 안, 길이·폭·비아 수는 조건 5 저촉) · dev 리포에는 원자료만 있다(선분 양 끝점과 심볼, get_line_width, 넷 서브넷의 FID, 넷→층 역색인) — POST /jobs/{id}/viewer/net 이 넷 하나·층 하나의 동박 다각형과 bounds 를 쓴다 · cae00 문서에 넷 형상 조회 없음
- 빠진 것 — 넷 단위로 길이·폭·비아 수를 합산하는 계산이 없다(새 계산). P0 질문(충전 대전류 경로의 최소 배선 폭·층 전환 비아 수)에 답하려면 조건 5 의 트레이스 폭·비아 제외를 깨야 한다. 전류·전압은 ODB++ 에 없다. 행 상태가 in_repo_not_exposed 3·contract_only 1 로 갈렸으나 값을 내는 코드가 없어 partial 이다(soc-mem-61 의 contract_only 는 경유 층에만 해당 — 비평 수용)
- 풀리는 도메인(7) — pwr · rf · mem · soc · sim · cam · disp
- 메커니즘 — electrical.si_pi · thermal.hotspot · new:thermal.charging_heat · new:electrical.rf_path_loss · electrical.net
- 질문 예 — 충전 대전류 경로의 넷별 최소 배선 폭·층 전환 비아 수는 얼마인가 / 안테나 급전점에서 튜너·LNA 까지 RF 선로의 길이·폭·층은 / LPDDR·UFS 고속 넷의 경유 층·길이·비아 수는 얼마인가
- 선행 — ECAD-17 · ECAD-04 · other: 넷 전압·전류(전원 트리)
- 근거 — ODB/src/models.py:273-283,386-407 · ODB/src/parsers/symbol_resolver.py:465 · ODB/src/services/viewer_service.py:126-157 · ODB/api/routers/viewer.py:74-82 · ODB/src/checklist/geometry_utils/clearance.py:257 · ODB/src·api grep 'trace_length|net_length'(0건) · CACHE eda_data.json(TRC 472·VIA 9,394·PLN 359) · CONTRACT 조건 5

#### ECAD-20 · 같은 넷을 공유하는 핀 쌍 거리 — 디캡·핫루프·보호소자

**부분 · P1**

- 돌려줘야 하는 것 — 질의(net 또는 ic_refdes) → pairs[]{net_name, a{refdes, pin}, b{refdes, pin}, distance_mm(패드 간·중심 간 구분), same_side} · IC 전원 핀별 caps[]{refdes, value, size_code, side, distance_to_pin_mm}·count
- 지금 — 계약 밖 · dev 리포에는 원자료와 일반 거리 함수가 있다(핀별 넷·좌표, pad_to_pad_distance, find_capacitors, VALUE 속성) — 넷을 지정해 쌍을 고르는 계산은 없다 · cae00 문서는 부품별 핀까지
- 빠진 것 — 넷 역조회와 쌍 선택이 새 계산이다. 전원 넷 판별이 없고(이름 판별은 GND 집합뿐, 규칙 파일에 전원·임피던스 낱말 0건) 보호소자 분류도 없다. 직선거리까지만 가능하다. pwr-26 이 P0 였으나 그 P0 는 핀 표(ECAD-18)가 받는다 — 핀 좌표가 오면 거리는 결정론적 산술이라 P1 로 둔다. 좌석 계약이 도구 결과 수치의 인용을 요구하므로 한 곳이 값을 내야 한다
- 풀리는 도메인(5) — pwr · soc · mem · passive · rf
- 메커니즘 — electrical.si_pi · electrical.emi · new:electrical.esd_path · new:electrical.eos_esd_path
- 질문 예 — 입력 캡과 IC VIN·PGND 핀, 인덕터와 SW 핀 사이 거리는 얼마인가 / AP 전원 볼 근처 디커플링 캡의 개수와 거리는 얼마인가 / TVS 에서 같은 넷의 커넥터 핀까지 거리는 얼마인가
- 선행 — ECAD-18 · ECAD-12 · ECAD-13
- 근거 — ODB/src/checklist/geometry_utils/clearance.py:117-159 · ODB/src/checklist/geometry_utils/distance.py:26-55 · ODB/src/checklist/rules grep 'impedance|thermal|decoupl|전원'(0건) · DELIB:582-590 · REF §4.6

#### ECAD-21 · 고속·RF 넷의 SI 기하 — 차동쌍 편차·기준 플레인 연속성

**부분 · P1**

- 돌려줘야 하는 것 — 넷 그룹(MIPI·LPDDR·UFS·USB·RF·클럭)별 {구간 선폭·간격[µm], 층, 길이[mm], 쌍 내 길이차[mm], 비아 전이 수, 스텁 길이[mm], ref_layer, 기준 플레인 분할 횡단 수와 좌표[mm]·gap_width[mm], 횡단점에서 최근접 스티칭 비아까지 거리[mm]}
- 지금 — 계약 밖(조건 5 저촉) · dev 리포에는 원자료만 있다(층별 선·면 피처, 넷↔피처 대응) — 넷 클래스·차동쌍·기준 플레인 분석 코드가 없고 38규칙에도 SI·EMI 규칙이 없다(Placement 33·Spacing 1·Clearance 4) · cae00 문서에 해당 도구 없음
- 빠진 것 — 전부 새 계산이다. 차동쌍·넷 그룹을 가를 근거가 데이터에 없다(샘플 넷 속성 0, 이름 패턴뿐). 비평 제안 둘(SI 기하 요약·리턴 패스 횡단)을 검증해 합쳤다
- 풀리는 도메인(7) — mem · soc · cam · disp · pcb · rf · xd
- 메커니즘 — electrical.si_pi · electrical.emi · new:electrical.desense
- 질문 예 — 고속 넷 묶음이 기준 플레인 위를 끊김 없이 달리고 쌍 안의 편차가 얼마인가 / 고속·RF·클럭 넷이 기준 플레인의 분할·슬롯을 가로지르는가
- 선행 — ECAD-19 · ECAD-17 · ECAD-04
- 근거 — ODB/src·api grep 'net_class|impedance|differential'(코드 0건) · ODB/src/checklist/rules(category 집계 33·1·4) · ODB/src/models.py:273-365 · CACHE eda_data.json·layers/plane_4.json · GW list_agents(domain='xd-ecad') xd-ecad-routing

### 패드·비아·트레이스·드릴

#### ECAD-22 · 핀별 랜드 패드 치수·SMD/NSMD·마스크 개구

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — pads[]{refdes, pin_name, pad_shape, pad_w_um·pad_l_um(또는 pad_dia_um), symbol_name, symbol_unit(mil|µm), mask_opening_um, pad_def(SMD|NSMD|unknown), 패드 간격_um} + 부품별 대표 pad_size_um(원형 패드 최빈값)
- 지금 — 계약 밖(조건 5 저촉) · dev 리포 산출(패드 심볼 이름 — parts.json 의 pins[].pad, 심볼을 치수로 푸는 get_symbol_size, 마스크 층 피처) · cae00 문서 get_part_detail.pins[].pad 가 심볼 코드만. GW sed_sample_from_odb 가 그 심볼의 최빈값을 pad_size 로 읽는다
- 빠진 것 — 치수(µm)로 풀어 주는 칸이 없다 — 심볼 숫자가 파일 단위에 따라 mil 또는 µm 이라 받는 쪽이 풀면 틀리기 쉽다. SMD/NSMD 판정과 마스크 개구 대조는 새 계산이다(마스크 대조는 인터포저 전용 CKL-01-009 뿐). predict_sed 가 pad_size 를 필수로 받으므로 P0 질문(SED 예측 입력)에 답하려면 조건 5 의 패드 제외를 깨야 한다
- 풀리는 도메인(6) — soc · mem · sim · pcb · passive · rel
- 메커니즘 — electrical.pad_lift · thermal.solder_fatigue · mechanical.drop_stress · new:process.tombstone · process.solder
- 질문 예 — AP 랜드 패드 지름과 SMD/NSMD 정의는 어떤가 / 0603 이하 2단자 칩의 양 패드 치수가 비대칭인가 / SED 예측 입력(패키지 패드 크기)
- 선행 — ECAD-18 · ECAD-02
- 근거 — ODB/src/models.py:454-470 · ODB/src/parsers/symbol_resolver.py:441 · ODB/src/services/extract_service.py:48 · ODB/src/checklist/rules/ckl_01_009.py · ODB/documents/ODB_RULES.md §6 · CACHE components_top.json(geom.symbol_name)·layers/soldermask_top.json · CONTRACT 조건 5 · GW predict_sed 스키마 · REF 대조 #3

#### ECAD-23 · 패드별 비아 수·NC 패드·코너 핀 판정

**리포에 있음 · 미노출 · P1**

- 돌려줘야 하는 것 — pads[]{refdes, pin_name, net_name, is_nc(판정 근거), is_corner, is_outermost, via_count(개), via_in_pad}
- 지금 — 계약 밖(조건 5 저촉) · dev 리포 산출(build_via_position_set·count_vias_at_pad, is_pad_nc, find_outermost_pin_indices) — 규칙 CKL-01-002·03-001·03-004 등 안에서만 쓴다 · cae00 문서는 규칙 결과 행으로만 간접
- 빠진 것 — 임의 부품·핀에 값을 주는 조회가 없다(규칙 대상이 한정되고 AP 는 대상이 아니다). 비아는 위치만 세고 지름·층 구간을 내지 않는다
- 풀리는 도메인(5) — soc · mem · passive · pcb · sh
- 메커니즘 — electrical.pad_lift · electrical.si_pi · mechanical.drop_stress
- 질문 예 — AP 코너 볼의 NC 여부와 패드 비아 유무는 어떤가 / 디커플링 캡 패드별 비아 수는 얼마인가
- 선행 — ECAD-18
- 근거 — ODB/src/checklist/geometry_utils/via.py:22-105,416-462 · ODB/src/checklist/geometry_utils/nc_pad.py:31,238 · ODB/src/checklist/rules/ckl_01_002.py·ckl_03_001.py · CONTRACT 조건 5

#### ECAD-24 · 드릴 층 구간 표와 구간별 비아 수

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — drill_layers[]{name, start_layer, end_layer, span_kind(microvia|buried|through 추정), hole_count, diameters_um[], geometry_names[]}
- 지금 — 계약 밖(조건 5 저촉) · dev 리포 산출(매트릭스 start_name·end_name 과 드릴 층 피처 — 샘플 d_1_2 3,185개·d_2_3 2,399개·d_3_8 1,305개·d_8_9 1,239개·d_9_10 1,261개, .geometry 'microvia0.100_round0.275') — dev REST /layers 는 name·type 만 · cae00 문서 get_board_layers 가 DRILL 층 이름까지
- 빠진 것 — 구간과 개수를 주는 응답이 없다. 구간 표만으로 스택 단수의 상한을 말할 수 있어 P0 질문(마이크로비아 몇 단 스택인가)에 답하려면 조건 5 의 비아 제외를 깨야 한다. 드릴 공구표는 경로만 찾고 파싱하지 않는다
- 풀리는 도메인(2) — pcb · rel
- 메커니즘 — new:reliability.microvia_fatigue · thermal.thermal_shock
- 질문 예 — 마이크로비아가 몇 단 스택이고 어느 층 구간에 있는가
- 선행 — ECAD-04
- 근거 — ODB/src/models.py:154-171,527-545 · ODB/src/parsers/matrix_parser.py:44-45 · ODB/src/odb_loader.py:232 · CACHE matrix_layers.json(드릴 7층 구간)·layers/d_*.json(개수·심볼·.geometry 실측) · CONTRACT 조건 5 · REF §3

#### ECAD-25 · 비아 구조 상세 — 좌표·지름·구간·적층·스태거·필·홀벽 간격

**부분 · P1**

- 돌려줘야 하는 것 — vias[]{x_mm, y_mm, drill_dia_um, land_dia_um, start_layer, end_layer, net_name, stacked_levels, staggered, filled(bool|unknown), plating} + 이종 넷 홀벽 최소 간격_um
- 지금 — 계약 밖(조건 5 저촉) · dev 리포에는 원자료만 있다(드릴 층 패드의 x·y·심볼 지름·.geometry 이름·층 구간, EDA VIA 서브넷) — via.py 는 위치 집합과 패드 안 개수만 낸다 · cae00 문서에 비아 조회 없음
- 빠진 것 — 적층 단수·스태거 판정·넷 대응·홀벽 간격은 새 계산이다. 필 여부와 도금은 데이터에서 찾지 못했다(드릴 공구표 미파싱). 비평은 홀벽 간격을 '어디에도 없음' 으로 봤으나 홀 좌표와 지름은 드릴 층 패드 심볼로 파싱돼 있다
- 풀리는 도메인(3) — pcb · rel · soc
- 메커니즘 — new:reliability.microvia_fatigue · electrical.creepage · material.corrosion
- 질문 예 — BGA 패드 아래 via-in-pad 는 몇 개이고 스택인가 스태거인가 / 이종 전위 비아 홀벽 간격은 얼마인가
- 선행 — ECAD-24 · ECAD-17
- 근거 — ODB/src/checklist/geometry_utils/via.py:22-105 · ODB/src/models.py:527-545 · ODB/src·api grep 'microvia|blind|buried'(0건) · CACHE layers/d_1_2.json·d_3_8.json · CONTRACT 조건 5

#### ECAD-26 · 패드별 페이스트·마스크 개구와 연결 동박(SMT 공정 창)

**부분 · P1**

- 돌려줘야 하는 것 — pads[]{refdes, pin_name, pad_w·pad_l_um, paste_aperture_w·l_um, paste/pad 면적비, mask_opening_um, mask_dam_min_um, 연결 트레이스 폭_um·개수, 플레인 직결(bool)} — 스텐실 두께[mm]를 입력으로 받아 개구 면적비를 낸다
- 지금 — 계약 밖(조건 5 저촉) · dev 리포에는 원자료만 있다(SOLDER_PASTE 층의 패드와 심볼 — 샘플 spt 패드 2,118개, 솔더마스크 패드 2,267개, 신호층 선·면) · cae00 문서에 해당 도구 없음
- 빠진 것 — 페이스트 개구를 핀에 대응시키는 계산, 면적비, 마스크 댐 폭, 패드↔트레이스 연결 추적이 없다. 피듀셜 식별도 없다. 스텐실 두께는 공정 데이터다. 제안이 물은 '페이스트 층을 실제로 읽어 보관하는가' 는 샘플 캐시로 확인했다 — 보관한다
- 풀리는 도메인(4) — pcb · passive · rel · soc
- 메커니즘 — process.solder · new:process.tombstone · thermal.solder_fatigue
- 질문 예 — 패드별 페이스트 개구가 스텐실 면적비 한계를 지키는가 / 0603 이하 2단자 칩의 패드에 붙은 동박이 비대칭인가
- 선행 — ECAD-22 · ECAD-18 · other: 공정 데이터(스텐실 두께)
- 근거 — ODB/src/models.py:20-33 · ODB/src/parsers/feature_parser.py:20-160 · CACHE matrix_layers.json(SOLDER_PASTE 2층)·layers/spt.json(pad 2,118, 심볼 66종) · ODB/src·api grep 'paste|fiducial'(계산 코드 0건) · CONTRACT 조건 5

#### ECAD-27 · 이종 넷 도체·패드 최소 간격(연면)

**부분 · P1**

- 돌려줘야 하는 것 — 질의(영역·넷 쌍·부품) → min_spacing_um, 위치 x·y, 두 넷 이름, 층, 표면/내층 구분 · 부품 안 인접 패드 간 최소 간격
- 지금 — 계약 밖(조건 5 저촉) · dev 리포에는 부품 쌍의 패드 간 최소 거리 함수와 쉴드캔 한 부품 안 패드 쌍 최소거리(CKL-03-003)만 있다 — 넷 기준 도체 간격 계산은 없다 · cae00 문서에 해당 도구 없음
- 빠진 것 — 넷을 지정하는 도체 간격 계산이 새로 필요하다. 넷 전압 등급이 ODB++ 에 없어 연면 기준을 고를 수 없다. 행은 P2 였으나 같은 능력을 묻는 pwr-35 가 P1 이라 P1 로 올린다(비평 일부 수용). P0 로는 올리지 않는다 — 전압 등급 없이는 간격 수치가 판정으로 이어지지 않는다
- 풀리는 도메인(4) — std · rel · pwr · pcb
- 메커니즘 — electrical.creepage · material.corrosion · new:electrical.eos_esd_path
- 질문 예 — USB Type-C 입력부 인접 이종 넷 패드 간 최소 간격은 얼마인가 / 이종 넷 도체 최소 간격
- 선행 — ECAD-17 · ECAD-18 · other: 넷 전압 등급
- 근거 — ODB/src/checklist/geometry_utils/clearance.py:117-159 · ODB/src/checklist/rules/ckl_03_003.py:1-12

#### ECAD-28 · 테스트포인트·노출 패드 목록

**리포에 있음 · 미노출 · P2**

- 돌려줘야 하는 것 — test_points[]{tp_id, net_name, side, x_mm, y_mm, pad_dia_um, 식별 근거(refdes TP 접두|DESCRIPTION|.test_point 속성)} · 전원·핵심 넷 커버리지 % · 부품에 속하지 않은 노출 패드 목록
- 지금 — 계약 밖 · dev 리포 산출 일부(부품으로 배치된 테스트포인트는 Component 로 파싱된다 — 샘플에 refdes TP 접두 23개, DESCRIPTION 'TESTPOINT', 핀 1개와 넷 보유) — 가리는 코드는 없고 Unknown 이라 추출에서 빠진다 · cae00 문서에 해당 도구 없음
- 빠진 것 — 부품형 테스트포인트는 ECAD-09 가 Unknown 을 포함해 내면 그대로 나온다. 피처 속성 .test_point 는 샘플 속성 이름표에 있으나 쓰인 피처가 0개다(실보드 unverified). 커버리지와 노출 패드 식별은 새 계산이다. 제안은 P1·P2 였는데 P2 로 둔다 — 받는 좌석이 좁고 대부분 ECAD-09 로 충족된다. 제안의 'ODB 에 테스트포인트가 없다' 는 코드에만 맞고 데이터에는 있다
- 풀리는 도메인(3) — pcb · rel · xd
- 메커니즘 — new:process.test_access · new:electrical.esd_path · material.corrosion
- 질문 예 — 검사와 고장 위치 특정에 쓸 테스트포인트가 있고 어느 넷에 붙어 있는가
- 선행 — ECAD-09 · ECAD-18
- 근거 — CACHE components_top.json(TP 12개)·components_bot.json(TP 11개)·layers/signal_1.json(attr_names 에 .test_point, 사용 0) · ODB/src·api grep 'test_point|testpoint'(0건) · ODB/src/checklist/rules/ckl_03_015.py:44

### 영역

#### ECAD-29 · 쉴드캔 풋프린트·내벽·구획과 구획별 내부 부품

**리포에 있음 · 미노출 · P1**

- 돌려줘야 하는 것 — shield_cans[]{refdes, side, outline(bbox·면적 또는 다각형 참조), inner_walls[], regions[]{id, kind(inside_pocket|main), refdes[]}} · membership[]{refdes, shield_can_refdes, region, distance_to_wall_mm}
- 지금 — 계약 밖 · dev 리포 산출(find_shield_cans, detect_inner_walls·split_interior_by_inner_walls·classify_inner_region, find_components_inside_outline) — 규칙 CKL-02-005·007 안에서만 쓴다 · cae00 문서는 Shield Can 개수 집계와 규칙 결과 행까지
- 빠진 것 — 구획별 부품 목록·소속을 돌려주는 조회가 없다. 다각형은 ODB 규격서의 '지오메트리를 도구 결과로 반환하지 않는다' 원칙과 부딪혀 소속·거리 같은 요약 값으로 내야 한다. 캔의 3D 높이는 MCAD 와 이어야 한다
- 풀리는 도메인(6) — soc · mem · rf · pcb · passive · mech
- 메커니즘 — thermal.hotspot · electrical.emi · new:electrical.desense · interface.clearance_close
- 질문 예 — 같은 쉴드캔 구획 안의 동시 발열 조합은 무엇인가 / 노이즈원과 LNA 입력이 같은 쉴드캔 구획 안인가
- 선행 — ECAD-09 · ECAD-12
- 근거 — ODB/src/checklist/geometry_utils/shield_can.py:47,430,576,645 · ODB/src/checklist/geometry_utils/overlap.py:1015 · ODB/src/checklist/component_classifier.py:235-237 · ODB/documents/MCP_INTEGRATION.md §2.2 · REF §4.4

#### ECAD-30 · 쉴드캔 접지 패드 배열 — 테두리 최대 개구·패드 피치·패드별 GND 비아

**부분 · P1**

- 돌려줘야 하는 것 — shield_cans[]{refdes, pad_count, pad_pitch_mm(중앙값·최대), max_opening_mm, opening_at[x, y], vias_per_pad[], gnd_net}
- 지금 — 계약 밖(조건 5 저촉) · dev 리포에는 원자료와 일부 계산이 있다(캔 패드 다각형·외곽·fill-cut 검출, 패드 안 비아 계수, parts.json 의 캔 핀 좌표) — CKL-03-003 은 패드 쌍 최소거리만 본다 · cae00 문서에 패드 조회 없음
- 빠진 것 — 테두리 방향 최대 개구는 어디서도 계산하지 않는다(새 계산). 캔–프레임 접촉은 MCAD 에서 와야 한다
- 풀리는 도메인(3) — rf · mech · xd
- 메커니즘 — electrical.emi · new:electrical.desense · interface.tied
- 질문 예 — 쉴드캔–PCB 접지 접촉이 테두리를 따라 끊긴 구간의 최대 길이는 / 쉴드캔 GND 접촉(솔더 패드) 피치는 얼마인가
- 선행 — ECAD-29 · ECAD-18 · ECAD-23
- 근거 — ODB/src/checklist/geometry_utils/shield_can.py:47-62,843 · ODB/src/checklist/geometry_utils/via.py:416 · ODB/src/checklist/rules/ckl_03_003.py:1-12 · ODB/src/services/extract_service.py:37-73 · CONTRACT 조건 5

#### ECAD-31 · 지정 영역의 층별 동박 침범 — 안테나 클리어런스

**부분 · P0**

- 돌려줘야 하는 것 — 입력 region(다각형 또는 bbox[mm], 보드 좌표) → layers[]{layer, type, copper_ratio(0~1), has_plane, nearest_copper_edge_mm, 침범 넷 이름[]}. 도전층 전체
- 지금 — 계약 밖 · dev 리포에는 격자 구간 동박률과 층별 동박 형상 빌더가 있다 — 임의 영역 질의와 에지 거리는 없다 · cae00 문서 get_copper_result 도 격자 구간(성공 표본 없음)
- 빠진 것 — 임의 다각형과의 교차·최근접 에지 거리가 새 계산이다(형상 빌더가 있어 교차 연산만 얹으면 된다). 계산이 SIGNAL 층만 돌아 GND 플레인이 빠진다 — 이 질문의 핵심이 플레인 침범이다. 안테나 투영 영역을 보드 좌표로 옮기는 변환은 어디에도 없다
- 풀리는 도메인(1) — rf
- 메커니즘 — new:electrical.antenna_detune · electrical.emi
- 질문 예 — 안테나 클리어런스 영역 안에 PCB 동박·GND 플레인이 들어와 있는가, 층별로 얼마나인가
- 선행 — ECAD-07 · ECAD-04 · join: 보드 좌표계→어셈블리 좌표계 변환
- 근거 — ODB/src/visualizer/copper_vector.py:478,616,646 · ODB/src/services/copper_service.py:77-80 · REF §2·§4.13 · CONTRACT

#### ECAD-32 · 플렉스·벤드·리지드 영역과 보강판·커버레이

**리포에 있음 · 미노출 · P1**

- 돌려줘야 하는 것 — areas[]{kind(bend|flex|rigid|stiffener|coverlay), bbox·면적(또는 다각형 참조), 관련 층[]} · 영역 안 {via_count, pad_count, 배선 주방향_deg, 넷 수} · flex 동박층 목록
- 지금 — 계약 밖 · dev 리포 산출(매트릭스 add_type BEND_AREA·FLEX_AREA·RIGID_AREA·STIFFENER·COVERLAY·PG_FLEX 와 그 층의 피처 — 샘플 bend_area·flex_area·rigid_area 에 surface 1개씩) — COVERLAY 만 규칙 둘이 마스크 층 고를 때 쓰고 나머지 영역 층을 읽는 코드는 없다 · cae00 문서에 해당 도구 없음
- 빠진 것 — 영역을 주는 조회와 영역 안 비아·패드 수·배선 방향 집계가 없다(집계는 새 계산). FPCB 가 ODB 잡으로 올라오는지는 unverified. 굽힘 반경은 MCAD 값이다. disp-cam-20 은 missing 이었으나 샘플 캐시에 영역 면이 실제로 파싱돼 있다(데이터는 FLEX enum 이 아니라 add_type 으로 온다)
- 풀리는 도메인(3) — pcb · disp · cam
- 메커니즘 — new:mechanical.fpcb_bend_radius · mechanical.fatigue
- 질문 예 — FPCB·리지드플렉스 굽힘 영역 안에 비아·패드가 있는가 / 패널 FPCB 의 층 구성과 보강판 경계는 무엇인가
- 선행 — ECAD-04 · ECAD-24
- 근거 — CACHE matrix_layers.json(row 12~17·41~43 add_type 실측)·layers/bend_area.json·flex_area.json·rigid_area.json·stiffener.json · ODB/src·api grep 'bend_area|flex_area|rigid_area|stiffener'(0건)·'COVERLAY'(ckl_01_009.py:75·ckl_02_005.py:103) · REF §3

#### ECAD-33 · 킵아웃·킵인·높이 제한 영역

**없음 · P2**

- 돌려줘야 하는 것 — areas[]{kind(comp_keepout|comp_keepin|route_keepout|via_keepout|plane_keepout|max_height|min_height), bbox·면적(또는 다각형 참조), 적용 층·면, 값(mm)}
- 지금 — 계약 밖 · dev 리포에 코드가 없다 — 샘플 층 피처의 속성 이름표에는 .drc_comp_keepout·.drc_route_keepout·.drc_max_height 등이 정의돼 있으나 그 속성을 가진 피처는 0개다(fab_drc 층의 'Rule Area' 면 9개는 .drc_etch_lyrs_bit·.area_name 만) · cae00 문서에 해당 도구 없음
- 빠진 것 — 실제 사내 보드에 킵아웃 속성이 실려 오는지부터 unverified 다. 검증된 행이 없고 과업의 그룹 지정 항목이라 직접 확인해 넣었다. 기구 유래 킵아웃은 MCAD 투영에서 와야 하므로 P2 다. 캐비티·임베디드 부품도 파서에 없다
- 풀리는 도메인(4) — xd · pcb · rf · mech
- 메커니즘 — interface.clearance · new:electrical.antenna_detune
- 질문 예 — 부품 킵아웃·높이 제한 영역을 침범한 부품이 있는가
- 선행 — ECAD-34
- 근거 — ODB/src·api grep 'keepout|keepin|cavity|drc_'(0건) · CACHE layers/*.json 속성 사용 집계(.drc_etch_lyrs_bit 9·.area_name 9 외 .drc_* 0)·layers/fab_drc.json

### 보드 기구

#### ECAD-34 · 보드 외곽 다각형·컷아웃과 굽힘 취약 협폭부

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — outline{contours[]{is_island, 꼭짓점[mm]}, bbox[4], area_mm2, x_mm·y_mm} · cutouts[]{bbox, area} · narrow_regions[]{id, bbox, width_mm(국부 최소 폭), depth_mm(돌출), 임계값, refdes_inside[], screw_nearby(bool|unknown)}
- 지금 — 계약 일부(outline_bbox[4] 만) · dev 리포 산출(profile 파서의 contours, build_board_polygon, find_bending_vulnerable_areas — 폭 8 mm 이하·돌출 2 mm 이상 다각형, CKL-03-011·CKL-01-010 이 쓴다) — REST 에 외곽 단독 경로가 없다 · cae00 문서는 보드 가로·세로·외곽 면적과 규칙 위반 행까지
- 빠진 것 — 계약이 bbox 4값뿐이라 돌출부·컷아웃이 IR 에서 사라진다. 협폭부 함수는 다각형만 돌려주고 폭·돌출 값을 칸으로 내지 않는다. CKL-01-010 은 스크류 검출이 미구현이라 협폭부를 전부 screw=FALSE·FAIL 로 낸다. 다각형은 ODB 규격서의 지오메트리 미반환 원칙과 부딪혀 꼭짓점 상한이나 리소스 참조가 필요하다. 심사 IR 에 보드·피처 노드 종류가 없다
- 풀리는 도메인(7) — pcb · rel · xd · mech · soc · sh · passive
- 메커니즘 — mechanical.bending · interface.clearance · mechanical.drop_stress · new:sensor.mounting_stress_offset · new:mechanical.board_strain
- 질문 예 — 보드 외곽에서 폭 8 mm 이하로 돌출한 협폭부와 컷아웃은 어디이고 그 안에 어떤 부품이 있는가 / 보드 외곽·협폭 돌출부와 프레임 포켓 사이 외곽 여유는 얼마인가
- 선행 — ECAD-02 · 심사 앱: rr_ir 보드·피처 노드 종류
- 근거 — ODB/src/parsers/profile_parser.py:11-24 · ODB/src/checklist/geometry_utils/clearance.py:39-57 · ODB/src/checklist/geometry_utils/bending.py:16-62 · ODB/src/checklist/rules/ckl_01_010.py:1-16 · ODB/src/services/viewer_service.py:105-111 · CONTRACT · PLAN:721 · ODB/documents/MCP_INTEGRATION.md §2.2 · REF §4.11

#### ECAD-35 · 고정홀·툴링홀·컷아웃 목록

**부분 · P0**

- 돌려줘야 하는 것 — holes[]{id, x_mm, y_mm, diameter_mm, nominal_mm, plating(PLATED|NON_PLATED), kind(mount|tooling|acoustic|other), net_name|null, 식별 근거(.mount_hole 속성|BOTHHOLE 부품|드릴 층), confidence} · hole_count · cutout_count
- 지금 — 계약 밖 · dev 리포에는 원자료와 제한된 판만 있다(드릴 층 패드의 x·y·심볼 지름·.mount_hole 속성·.geometry 이름 — 샘플 6개, 'hole2.000_np'·'hole1.500_npth'; BOTHHOLE 접두 부품을 고르는 find_bothholes 는 좌표만) · cae00 문서 get_mounting_holes(x·y·diameter_mm·plating·kind·confidence·cutout_count, 응답 표본 있음)
- 빠진 것 — dev 리포에 .mount_hole 을 읽어 홀을 엔티티로 뽑는 코드가 없다(grep 0건). BOTHHOLE 은 Unknown 이라 부품 목록에서도 빠지고 샘플에는 0개다. 드릴 공구표 미파싱이라 도금·finish size 가 없다. 홀의 넷(GND)과 음향 홀 구분은 어느 쪽에도 없다. 행 상태가 넷으로 갈렸는데 dev 기준으로는 partial 이다 — dev 리포 마지막 커밋이 2026-06-24 라 cae00 배포본보다 낡았다
- 풀리는 도메인(7) — pcb · mech · rel · soc · rf · sh · passive
- 메커니즘 — mechanical.drop_stress · new:mechanical.board_strain · electrical.pad_lift · new:electrical.ground_continuity · new:acoustic.port_alignment · process.screw_torque
- 질문 예 — PCB 지지 스팬(스크류 간 거리)은 얼마인가 / MEMS 마이크의 PCB 음향 홀 위치와 지름은 / PCB GND 를 잇는 접지 접점(스크류 홀)의 개수와 최대 간격은
- 선행 — ECAD-24 · ECAD-02
- 근거 — CACHE layers/d_1_10.json·d_5_6.json(.mount_hole 6개 실측) · ODB/src·api grep 'mount_hole|tooling_hole|get_mounting'(0건) · ODB/src/checklist/component_classifier.py:199-201,209-221 · ODB/src/checklist/rules/ckl_01_010.py:14-15·ckl_03_012.py:1-9 · ODB/src/models.py:527-545 · ODB git log(a56b8e8, 2026-06-24) · REF §4.10

#### ECAD-36 · 부품(패키지 코너·패드)↔고정홀 거리

**부분 · P0**

- 돌려줘야 하는 것 — 질의(refdes 또는 범주) → rows[]{refdes, 기준(패키지 코너|패드|중심), nearest_hole_id, distance_mm, 지지 스팬 안 위치 비(0~1)}
- 지금 — 계약 밖 · dev 리포에는 제한된 판만 있다(CKL-03-012 가 OSC 패드↔BOTHHOLE 거리 to_BTH 를 계산) · cae00 문서에는 같은 보드 좌표의 원자료(get_mounting_holes·get_part_detail)만
- 빠진 것 — 임의 부품에 대한 거리 계산 하나가 새로 필요하다 — 입력이 같은 보드 좌표라 좌표 정합 없이 ECAD 안에서 닫힌다. 보드에 구멍이 없는 기구 지지점(보스·클램프)까지의 거리만 ECAD↔MCAD 변환이 필요하다
- 풀리는 도메인(6) — pcb · passive · rel · soc · sim · mech
- 메커니즘 — mechanical.drop_stress · new:mechanical.board_strain · new:mechanical.mlcc_flex_crack · process.screw_torque · thermal.solder_fatigue
- 질문 예 — 대형 BGA 의 패키지 코너에서 가장 가까운 보드 고정홀까지 거리는 얼마인가 / MLCC 가 스크류 고정홀 중심에서 몇 mm 인가
- 선행 — ECAD-35 · ECAD-11 · ECAD-09
- 근거 — ODB/src/checklist/rules/ckl_03_012.py:57,123-124 · ODB/src/checklist/component_classifier.py:199-201 · REF §4.6·§4.10 · DELIB:582-590

#### ECAD-37 · 부품↔보드 외곽·협폭부 거리와 변 대비 각도

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — 질의(refdes 또는 범주) → rows[]{refdes, distance_to_outline_mm(부품 외곽 기준·패드 기준 구분), nearest_edge_angle_deg, 장축–변 사잇각_deg, on_outline_edge, in_narrow_region(영역 id)}. 통과한 부품의 거리도 낸다
- 지금 — 계약 밖 · dev 리포 산출(distance_to_outline·pad_distance_to_outline·get_nearest_outline_edge_angle·is_on_outline_edge) — 규칙 내부용 · cae00 문서는 CKL-03-015 위반 부품만 규칙 행으로
- 빠진 것 — 임의 부품의 거리 값을 돌려주는 조회가 없다 — 규칙은 문턱 통과 여부와 한정된 대상(03-015 는 IC·C·L, 03-011 은 OSC)만 낸다. 디패널 라인 기준 거리는 절단선 데이터가 없어 못 낸다
- 풀리는 도메인(5) — passive · pcb · soc · rel · sh
- 메커니즘 — new:mechanical.mlcc_flex_crack · new:process.depanel_stress · mechanical.bending · mechanical.drop_stress · electrical.pad_lift
- 질문 예 — MLCC 가 보드 외곽·컷아웃에서 몇 mm 이고 장축이 그 변과 수직인가 / AP 패키지 외곽에서 보드 외곽·협폭부까지 거리는 얼마인가
- 선행 — ECAD-34 · ECAD-09 · ECAD-14
- 근거 — ODB/src/checklist/geometry_utils/clearance.py:70-115 · ODB/src/checklist/geometry_utils/polygon.py:1040-1136 · ODB/src/checklist/rules/ckl_03_015.py:1-13,44,194 · REF §4.14

#### ECAD-38 · 임의 부품 쌍 거리 — 중심·외곽·패드 간

**리포에 있음 · 미노출 · P1**

- 돌려줘야 하는 것 — 질의(refdes_a, refdes_b 또는 a 와 범주·역할) → {center_distance_mm, edge_distance_mm, pad_to_pad_mm, same_side} · 사이에 낀 부품 refdes[]
- 지금 — 계약 밖 · dev 리포 산출(center_distance·edge_distance·pad_distance_to_component·pad_to_pad_distance·is_sandwiched_between) — 규칙 내부용 · cae00 문서에는 부품 좌표만
- 빠진 것 — 임의 쌍을 묻는 조회가 없다. 계약에는 좌표만 있어 좌석이 직접 셈해야 하는데 좌석 계약은 도구 결과 수치의 인용을 요구한다. 어느 부품이 발열원·노이즈원·센서인지는 역할 표(ECAD-12)가 정한다
- 풀리는 도메인(7) — soc · mem · sh · rf · passive · pwr · cam
- 메커니즘 — thermal.hotspot · new:sensor.thermal_drift · new:acoustic.component_noise · new:process.underfill_coverage · interface.clearance · new:electrical.desense · mechanical.vibration
- 질문 예 — 센서가 발열원(AP·PMIC·충전 IC) 가까이 있는가 / AP 와 메모리 패키지 간 간격은 얼마인가 / 코일 울음을 내는 인덕터·MLCC 가 마이크 가까이 있는가
- 선행 — ECAD-09 · ECAD-12
- 근거 — ODB/src/checklist/geometry_utils/distance.py:26-55 · ODB/src/checklist/geometry_utils/clearance.py:117-159 · ODB/src/checklist/geometry_utils/overlap.py:160 · DELIB:582-590

#### ECAD-39 · 반대면 중첩·미러 쌍 검출(임의 범주)

**리포에 있음 · 미노출 · P1**

- 돌려줘야 하는 것 — 질의(refdes 또는 범주 쌍) → pairs[]{refdes, opposite_refdes, opp_category, overlap_type(pad|outline), Δxy_mm, 공유 net[]} — 캡–캡·IC–IC 미러 쌍 포함
- 지금 — 계약 밖 · dev 리포 산출(find_overlapping_components·find_pad_overlapping_components — 후보 집합을 인자로 받는 일반 함수) — 규칙은 정해진 범주 쌍에만 건다 · cae00 문서는 규칙 결과 행만
- 빠진 것 — 임의 범주 쌍을 묻는 조회가 없다. 규칙에 없는 조합(고용량 MLCC 미러 쌍, BGA 끼리 미러 실장, X-ray 가 가려지는 양면 BGA)은 결과가 없다 — 대상 집합만 바꿔 부르면 된다. pcb-passive-57 은 partial 이었으나 일반 중첩 함수가 있어 이 상태로 정했다
- 풀리는 도메인(4) — passive · pcb · soc · mem
- 메커니즘 — new:acoustic.mlcc_singing · thermal.solder_fatigue · mechanical.drop_stress · process.solder
- 질문 예 — 고용량 MLCC 가 같은 x·y 의 반대면에 미러 쌍으로 놓였는가 / AP 반대면(같은 XY)에 겹쳐 실장된 부품은 무엇인가
- 선행 — ECAD-09
- 근거 — ODB/src/checklist/geometry_utils/overlap.py:59-160,937-1013 · ODB/src/checklist/rules/ckl_01_001.py·ckl_02_011.py · REF §4.14·§4.15

#### ECAD-40 · 판넬 배열·디패널 라인·탭

**부분 · P1**

- 돌려줘야 하는 것 — panel{nx, ny, dx_mm, dy_mm, n_units} · break_lines[]{type(v_cut|router|mouse_bite), 선분 좌표[mm]} · tabs[]{x, y}
- 지금 — 계약 밖 · dev 리포에는 판넬 배열만 있다(STEP-REPEAT 파싱, ROUT 층 피처) — 절단선·탭 식별은 없다. 샘플은 unit 데이터라 step_repeats 가 비어 있다 · cae00 문서 get_volume_result 의 array 스코프 n_units
- 빠진 것 — 절단선 종류·선분·탭을 식별하는 로직이 없고 unit 데이터에는 판넬 정보가 실리지 않는다. 공정 자료로 대신할 수 있다
- 풀리는 도메인(2) — pcb · passive
- 메커니즘 — new:process.depanel_stress
- 질문 예 — 디패널 라인은 어디이고 그 5 mm 안에 놓인 BGA·MLCC 는 무엇인가
- 선행 — ECAD-34 · other: 공정 데이터(디패널 방식)
- 근거 — ODB/src/parsers/stephdr_parser.py:54-57 · ODB/src/models.py:176-187 · CACHE step_header.json(step_repeats 0)·layers/rout.json · REF §4.11

### 체크리스트 결과

#### ECAD-41 · 체크리스트 규칙별 결과 — 규칙 id·판정·위반 refdes·좌표·상세 행

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — rules[]{rule_id(CKL-XX-NNN), category, description, status, recommended, violation_count, evaluated_n, affected[]{refdes, side, x_mm, y_mm}, details{columns[], rows[]}, 임계값} · 규칙 카탈로그(대상 범주·참조 목록·임계) · total·passed·failed
- 지금 — 계약 밖 · dev 리포 산출(규칙 38개 — Placement 33·Spacing 1·Clearance 4, RuleResult{rule_id, passed, message, affected_components, details{columns, rows}, recommended}, GET /api/rules 카탈로그) — dev REST 실행 결과는 passed·failed·total 과 HTML 뿐 · cae00 문서 get_checklist_result·get_rule_detail·get_violation_map·list_rules(요약·위반 좌표는 표본 있음, 행 칼럼은 unverified)
- 빠진 것 — 규칙별 JSON 이 dev 에서 나오지 않는다(값은 RuleResult 에 있다). 계약과 rr_ir 에 자리가 없다. 전기(SI·PDN·EMI) 규칙은 없다. 좌석 계약의 check_design_rules 는 Laminate Analyzer 의 복합재 적층 규칙이고 지금 backend_down 이다 — 계약이 뜻한 능력은 이 항목이다(비평 수용). dev 판 CKL-03-015 는 신호층 검사가 주석 처리인데 cae00 응답은 signal 57건을 센다 — 두 판이 다르다. 행 상태가 in_repo_not_exposed 9·have_not_ingested 10·partial 1 로 갈렸으나 dev 기준으로 통일한다
- 풀리는 도메인(12) — pcb · passive · soc · mem · pwr · rf · xd · rel · sh · cam · mech · std
- 메커니즘 — electrical.pad_lift · mechanical.bending · mechanical.drop_stress · thermal.solder_fatigue · process.solder · new:mechanical.mlcc_flex_crack · new:process.underfill_coverage · new:sensor.vent_path · electrical.emi
- 질문 예 — ECAD 배치 규칙 위반 중 기구와 맞물리는 것의 위반 refdes 와 좌표는 무엇인가 / 관리 캐패시터·인덕터가 반대면 커넥터·쉴드캔과 겹치거나 1.5 mm 안인가 / PMIC 최외곽 NC 패드·코너 볼 비아 위반은 어느 부품인가
- 선행 — ECAD-42 · ECAD-44 · ECAD-09 · 심사 앱: rr_ir 규칙 결과 노드 종류
- 근거 — ODB/src/checklist/rules(38개, category 집계) · ODB/src/models.py:549-561 · ODB/src/checklist/engine.py:49-83 · ODB/api/routers/checklist.py:44-53 · ODB/api/routers/meta.py:19-26 · ODB/src/checklist/rules/ckl_03_015.py:1-13 · DELIB:604-626,637,662-664 · LaminateAnalyzerMCP/app/mcp_server.py:212-219 · GW list_tool_apps(laminate backend_down) · REF §2·§4.14·§4.15

#### ECAD-42 · 결과 상태 어휘·평가 대상 수·참조 목록 진위·기계 판독 오류 코드

**없음 · P0**

- 돌려줘야 하는 것 — 규칙·분석 결과마다 status(pass|fail|not_run|not_applicable|error|reference_missing|reference_sample) · evaluated_n · violation_count · 모든 도구 응답의 error{code(not_run|not_found|not_ready|invalid_arg|truncated), retryable, next_call}
- 지금 — 계약에 없다 · dev 리포는 RuleResult.passed 불리언 하나이고 규칙이 예외를 던지면 passed=False 로 흡수한다. 참조 CSV 가 없으면 로더가 내장 샘플 CSV 를 만들어 쓰고 결과에 그 사실이 남지 않는다. dev REST 오류는 문장이다 · cae00 문서 — get_violation_map 은 미실행이면 빈 배열, get_copper_result 는 200 응답 안의 error 문장
- 빠진 것 — 미실행·대상 없음·평가 오류·참조 부재가 '위반 없음' 또는 '위반' 과 구별되지 않는다 — 좌석이 근거 없는 '위반 0건' 을 인용하게 된다. 참조 목록을 쓰는 규칙 파일이 17개인데 dev 의 CSV 6개는 전부 내장 샘플과 행 단위로 같고(직접 대조) pmic_list·dpad_capacitors·regular_sensors 는 없다. 오류가 문장이라 어댑터가 필수 호출 실패와 선택 호출 실패를 가를 수 없다. 비평 제안 둘을 검증해 합쳤고 P0 를 유지한다 — ECAD-41 을 근거로 쓰는 전제다
- 풀리는 도메인(6) — pcb · passive · soc · mem · pwr · rf
- 메커니즘 — new:process.evidence_integrity · electrical.pad_lift · mechanical.bending · process.solder
- 질문 예 — 위반 0건은 '검사해서 없었다' 인가 '검사하지 않았다' 인가 / 실패한 호출이 '아직 계산 안 함' 인지 '그런 잡이 없음' 인지를 코드가 가를 수 있는가
- 근거 — ODB/src/models.py:549-561 · ODB/src/checklist/engine.py:68-79 · ODB/src/checklist/reference_loader.py:23-111,128-155 · ODB/references(csv 6개, 샘플과 동일 — 스크래치 대조) · ODB/src/checklist/rules grep 'csv|reference'(17개 파일) · REF 대조 #8·#10·§4.13

#### ECAD-43 · 결과 판(版) 식별과 이력 보존

**없음 · P1**

- 돌려줘야 하는 것 — 결과마다 result_id · kind · completed_at · ruleset_version(규칙 코드 커밋) · parser_version(캐시 세대) · reference[]{file, sha256, is_sample} · params(rule_ids, copper method·n_rows·n_cols, old_job_id, 비교 문턱) · created_by. 덮어쓰지 않고 result_id 로 다시 읽는다. 조회 도구는 side_effects(none|stores_result|recompute)를 선언
- 지금 — 계약에 없다 · dev 리포는 결과를 kind 당 최신 1건으로 덮어쓴다(record_result 'latest wins') — 칸은 kind·report·summary·params·created_by·completed_at 뿐이다. 캐시에 세대 키가 없다 · cae00 문서 list_results, get_managed_parts 는 조회인데 결과를 저장한다
- 빠진 것 — rule_ids 를 일부만 준 실행이 38규칙 전체 결과를 대체한다. 규칙 코드가 바뀌어도 판 표식이 없어 저장된 pass→fail 전이를 설계 변경으로 인용할 수 없다. 다만 CKL-DIFF 는 비교 시점에 양쪽을 같은 엔진으로 다시 돌리므로 그 전이는 규칙 판이 같다. 제안은 P0 였으나 P1 로 둔다 — 단일 스냅샷 인용은 ECAD-42 로 성립하고 이 항목은 전이의 신뢰를 올린다. 읽기 도구 순수성 제안(CP-20)은 여기 result_id·side_effects 로 받는다
- 풀리는 도메인(6) — pcb · passive · soc · mem · pwr · rf
- 메커니즘 — new:process.data_comparability · new:process.evidence_integrity
- 질문 예 — 두 리비전의 체크리스트·동박률 차이는 보드가 바뀐 것인가, 규칙 코드·참조 목록·계산 옵션이 바뀐 것인가
- 선행 — ECAD-42
- 근거 — ODB/src/services/job_store.py:329-355 · ODB/workspace/e67cbbdf95044b0a/results.json(checklist 1건, 칸 6개) · ODB/src/cache_manager.py grep version(세대 키 없음) · ODB/src/comparator/comparators/checklist_diff.py:49-66 · DELIB:2066-2070 · REF §4.16·대조 #6

#### ECAD-44 · 관리부품 참조 목록(실목록과 해시)

**리포에 있음 · 미노출 · P1**

- 돌려줘야 하는 것 — lists[]{name(capacitors_10|capacitors_41|inductors_2s|hall_ic|axis_sensors|ap_memory|pmic_list|dpad_capacitors|regular_sensors), sha256, is_sample, rows[]{part_name, size, pad_geom_name, rank, category, maker, type}} · 보드별 사용 현황{part_name, size, top, bottom, total}
- 지금 — 계약 밖 · dev 리포 산출(reference_loader 가 CSV 를 읽어 규칙에 준다) — 다만 dev 의 CSV 6개는 로더가 만든 내장 샘플이고 pmic_list·dpad_capacitors·regular_sensors 는 없다(references/* 는 gitignore) · cae00 문서 get_managed_parts(캐패시터 10종·41종, 인덕터 2S 사용 현황, 표본 있음)
- 빠진 것 — 실제 사내 관리 목록이 dev 에 없어 dev 에서 돌린 참조 의존 규칙 결과는 믿을 수 없다. 목록의 해시가 결과에 실리지 않는다. AP·메모리·홀 IC·축 센서 역할 판정도 이 목록에 달려 있다. pcb-passive-51 은 have_not_ingested 였으나 dev 기준으로는 기구만 있고 실데이터가 없다
- 풀리는 도메인(6) — passive · pcb · soc · mem · sh · cam
- 메커니즘 — new:mechanical.mlcc_flex_crack · new:process.data_comparability
- 질문 예 — 이 보드의 규칙 대상(관리 캐패시터 10종·41종, 인덕터 2S)은 실제 사내 목록 기준인가
- 근거 — ODB/src/checklist/reference_loader.py:23-111,128-161 · ODB/references(csv 6개 identical_to_sample — 스크래치 대조) · ODB/.gitignore:216 · REF §3·§4.9

### 리비전 비교

#### ECAD-45 · 리비전 간 부품 변경 표 — 추가·삭제·이동·교체

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — changes[]{refdes, layer(Top|Bottom), change_type(ADDED|REMOVED|RELOCATED|MODIFIED), old·new{x_mm, y_mm, rot_deg, mirror}, ΔX_mm·ΔY_mm, ΔRot_deg, mirror_changed, part_name old→new} · 문턱(위치 0.01 mm·회전 0.1°) · old_job_id·new_job_id
- 지금 — 계약 밖(심사 diff 의 ecad.component_moved 는 예약 어휘) · dev 리포 산출(비교기 COMP-DIFF — refdes 로 면별 매칭, ComponentChange 에 Δ 값) — dev REST POST /api/compare 는 비교기별 한 줄 요약과 HTML 만 · cae00 문서 run_compare(쓰기) 뒤 get_compare_result·get_compare_table(칼럼 표본 없음)
- 빠진 것 — 변경 행을 JSON 으로 주는 응답이 dev 에 없다. 심사 diff 에 ecad 이벤트를 만드는 코드가 없다(diff.py 에 ecad 0건, 스키마 어휘 한 줄) — 부품이 rr_ir 노드로 실리면 심사 diff 가 같은 일을 할 수 있어 둘 중 한 길을 정해야 한다. 비교는 실행형이라 좌석이 부를 수 없다. 기준이 part_name 하나라 벤더·MPN 만 바뀐 교체는 안 잡힌다. 행 상태가 in_repo_not_exposed 6·have_not_ingested 3·partial 1 로 갈렸으나 dev 기준으로 정했다
- 풀리는 도메인(9) — pcb · soc · mem · rf · pwr · passive · xd · rel · sh
- 메커니즘 — electrical.net · mechanical.drop_stress · thermal.thermal_shock · material.supplier_change · interface.clearance_close · new:electrical.antenna_detune · new:sh.placement_change
- 질문 예 — base→target 에서 이동·추가·삭제·교체된 부품은 무엇인가(ΔX·ΔY·ΔRot) / AP 가 리비전에서 얼마나 옮겨졌는가 / 리비전 사이에 RF 부품이 이동하거나 품번이 바뀌었는가
- 선행 — ECAD-01 · ECAD-09 · 심사 앱: ecad.* diff 이벤트 생산 코드
- 근거 — ODB/src/comparator/comparators/component_diff.py:11-93 · ODB/src/comparator/base.py:38-60 · ODB/api/routers/compare.py:15-55 · ODB/documents/MCP_INTEGRATION.md §4.1 · PLAN:1582 · RISK/backend/app/diff.py(ecad grep 0건)·schemas/rr_diff.v1.json:318 · REF §2

#### ECAD-46 · 체크리스트 전이 — 리비전 간 FIXED·REGRESSED·STILL_FAIL

**리포에 있음 · 미노출 · P0**

- 돌려줘야 하는 것 — transitions[]{rule_id, transition(FIXED|REGRESSED|STILL_FAIL|STILL_PASS|NEW_RULE|REMOVED_RULE), old·new violation_count, 새로 위반한 refdes[], 양쪽 ruleset_version·참조 해시 일치 여부}
- 지금 — 계약 밖 · dev 리포 산출(비교기 CKL-DIFF — 비교 시점에 양쪽 리비전에 체크리스트를 다시 돌려 규칙별 전이를 낸다) — dev REST 는 요약 한 줄과 HTML · cae00 문서 get_compare_result 의 체크리스트 전이 집계
- 빠진 것 — 전이 행을 JSON 으로 주는 응답이 없다. 전이는 양쪽이 같은 규칙 세트·같은 참조 목록일 때만 설계 변경으로 읽을 수 있는데 그 표식이 없다. 비교기는 위반 부품을 개수로만 견준다
- 풀리는 도메인(6) — pcb · passive · soc · mem · pwr · rf
- 메커니즘 — mechanical.bending · electrical.pad_lift · process.solder
- 질문 예 — 38규칙 중 base 에서 PASS 였다가 target 에서 FAIL 로 바뀐 규칙과 위반 refdes·좌표는 무엇인가
- 선행 — ECAD-41 · ECAD-42 · ECAD-43
- 근거 — ODB/src/comparator/comparators/checklist_diff.py:45-66 · ODB/api/routers/compare.py:32-36 · REF §2

#### ECAD-47 · 넷·스택업·외곽·동박·BOM 비교

**부분 · P1**

- 돌려줘야 하는 것 — net_changes[]{net_name, 추가·삭제 핀, pin_set_hash old→new} · stackup_changes[]{layer key, Δthickness_um, material old→new, 층 추가·삭제} · outline_changes{Δ면적, 변한 구간} · copper_changes[]{layer, Δtotal_ratio} · bom_changes[]{refdes, vendor·mpn old→new} · hole_changes[]
- 지금 — 계약 밖(ecad.net_changed·stackup_changed 는 예약 어휘) · dev 리포에는 양쪽 리비전의 원자료만 있다 — 비교기는 COMP-DIFF·CKL-DIFF 둘뿐 · cae00 문서 get_compare_result 도 부품·체크리스트·관리부품 변경까지
- 빠진 것 — 넷·스택업·외곽·동박·벤더/MPN 비교기가 없다. 값이 rr_ir 노드 attrs 로 실리면 심사 diff 가 대신할 수 있다 — 그러려면 계약에 그 칸과 안정 키(층 키, pin_set_hash)가 먼저 있어야 한다
- 풀리는 도메인(6) — pwr · rf · mem · soc · pcb · passive
- 메커니즘 — electrical.net · material.supplier_change · process.warpage
- 질문 예 — 리비전 간 전원 넷 연결이 바뀌었나 / 보드 두께·층수·스택업이 리비전에서 바뀌었는가 / 품번이 같은 채 벤더·MPN 만 바뀐 소자 자리는 어디인가
- 선행 — ECAD-17 · ECAD-04 · ECAD-13 · ECAD-34
- 근거 — ODB/src/comparator/comparators(파일 2개) · ODB/src/comparator/comparators/component_diff.py:60-61,82-91 · PLAN:1582 · RISK/backend/app/schemas/rr_diff.v1.json:318 · REF §2

#### ECAD-48 · refdes 보조 식별 키와 리넘버링·면 이동 판정

**부분 · P1**

- 돌려줘야 하는 것 — components[]{refdes, stable_key(part_number + footprint + 핀–넷 서명 해시), odb_comp_id, renumber_suspect, side_changed, match_basis(refdes|stable_key|position)}
- 지금 — 계약 밖(심사 IR 키는 ecad:<refdes>) · dev 리포에는 원자료만 있다(Component.id·comp_index 를 파싱해 캐시에 둔다) — 비교기는 refdes 만으로 면별 대조한다 · cae00 문서에 해당 칸 없음
- 빠진 것 — 리넘버링은 전량 삭제+추가로, top→bottom 이동은 한 면 삭제와 다른 면 추가로 나온다. 보조 키 계산과 판정이 새로 필요하다. ODB++ 부품 ID 가 재출력에 유지되는지는 unverified
- 풀리는 도메인(6) — pcb · soc · mem · passive · pwr · rf
- 메커니즘 — electrical.net · material.supplier_change · interface.cross_file_untrusted
- 질문 예 — refdes 번호가 다시 매겨지거나 부품이 반대면으로 옮겨져도 같은 부품임을 알 수 있는가
- 선행 — ECAD-09 · ECAD-18
- 근거 — ODB/src/comparator/comparators/component_diff.py:16-27 · ODB/src/models.py:494-508 · CACHE components_top.json(id·comp_index 키) · PLAN:719,899-903

### 넣지 않은 것 — 11건

- 행 22건의 have_not_ingested 판정(pcb-passive-01·03·05·08·09·14·18·20·25·36·38·44·50·51·52·56·61·63·64·66, rf-12·38) — dev 게이트웨이에 ECAD 도구가 0종이라 '게이트웨이 도구가 돌려준다' 는 조건이 서지 않는다. cae00 27도구는 2026-09-16 문서 근거뿐이라 unverified 다. 전부 dev 기준으로 다시 매기고 cae00 문서 상태는 existing 에 따로 적었다(비평 3건 수용)
- CP-01 보드 피처를 스냅샷의 인용·비교 단위로 싣는 스키마(보드 노드·피처 노드) — 사실은 확인했다(PLAN:721 노드 종류 8종에 보드·피처가 없다). 다만 ECAD 쪽이 줄 능력이 아니라 심사 앱 rr_ir 스키마 변경이다. ECAD-34·35·41 의 depends_on 과 요약에 심사 앱 선행 조건으로 적었다
- CP-09 면별 부품 질량 대 패드 면적 비와 키 차이 큰 인접 쌍 — 별도 항목으로 두지 않고 ECAD-16 에 흡수했다. dev 리포에 질량·밀도가 없고(grep 0건) 값은 체적(16)·높이(10)·패드 치수(22)에서 유도되며 실장 순서는 공정 데이터다
- CP-17 값별 출처·신뢰 칸(thickness_source·material_source·height_source·role_source) — 별도 항목이 아니라 ECAD-04·05·06·10·12·35 의 반환 칸으로 흡수했다. cae00 의 thickness_source·stackup_verdict·confidence 는 문서 표본으로만 보았다
- CP-20 읽기 도구의 순수성 선언 — ECAD-43 의 result_id·side_effects 칸으로 받았다. dev 에는 MCP 서버가 없어 검증할 대상이 없고 get_managed_parts 가 결과를 저장한다는 것은 cae00 문서 근거뿐이다
- 비평(sim-rel-std-88)의 'P0 로 올려야 한다' 와 '홀벽 간격은 어디에도 없다' — P1 까지만 올렸다 — 넷 전압 등급이 ODB++ 에 없어 간격 수치가 판정으로 이어지지 않는다. 홀 좌표와 지름은 드릴 층 패드 심볼로 파싱돼 있고(샘플 d_1_2 r3.937·d_3_8 r7.874) 없는 것은 공구표의 도금·finish size 와 계산이다
- 비평(mech-xd-63·material-sh-48)의 xd·sh·cam·disp 좌석이 ECAD 없이 앉는 문제 — 사실은 확인했다(taxonomy 에서 xd·sh·cam·disp 의 ecad_dependent 가 false, list_agents 에 xd-ecad-placement·read·routing·rulecheck 실재). 조치는 ECAD 능력이 아니라 심사 앱의 좌석 단위 보류 판정이라 요약의 선행 조건으로 넘겼다. 해당 항목의 unlocks_domains 에는 이 도메인들을 넣었다
- 비평(pcb-passive-38)의 'std 대체 도구를 sim-rel-std-76 으로 바꾸라' — check_design_rules 가 복합재 적층 규칙이라는 지적은 확인해 ECAD-41 에 반영했다. std 대체 도구 지정은 ECAD 쪽 입력 행이 아니라 다른 목록의 일이다
- 행들이 함께 물은 부품 소비전력(disp-cam-31·material-sh-73·soc-mem-23)과 넷 전압·전류(pwr-16·pwr-35) — ODB 리포의 모델·파서·서비스 어디에도 없고 ODB++ 가 싣는 값이 아니다. ECAD 항목으로 만들지 않고 ECAD-12·19·20·27 의 depends_on 에 other 쪽 입력으로 적었다
- pwr-42 PCM 보드 자체의 ECAD 데이터 — 새 능력이 아니라 데이터 확보 문제다(팩 공급사 설계). 잡이 올라오면 ECAD-01 의 board_role·sibling_job_ids 와 기존 항목들이 그대로 받는다. 허브에 PCM 잡이 있는지는 unverified
- CP-19 의 '잡 삭제 REST 가 열려 있다' — 틀렸다. DELETE /jobs/{job_id} 는 관리자 비밀번호 헤더로 막혀 있다(ODB/api/routers/jobs.py:139-150). 무인증·자기 선언 이름이라는 나머지 지적은 맞아 ECAD-03 으로 넣었다

## 교차·해석·기타 — 67건

상태 분포 — 없음 34 · 부분 27 · 도구는 있음 · 스냅샷 미수집 3 · 리포에 있음 · 미노출 1 · 있음 1 · 계약에만 1. 우선순위 — P0 35 · P1 30 · P2 2.

### A 공유 식별 키

#### CROSS-01 · refdes ↔ MCAD 파트 ↔ 해석 pid 동일성 사전(same-as 원장)

**부분 · P0** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — 부품 인스턴스 1개당 1행 — {board_id, refdes, mcad canon_key(과제명 뗀 경로), dyna 안정 키(정규명@elem_class), method(ledger|pid_map|part_number_token|geometry|manual), score[0~1], status(auto|pending|confirmed|rejected), decided_by, decided_at}. 같은 품번 여러 자리는 자리마다 따로 낸다.
- 지금 — sameas.resolve 사다리와 rr_sameas 원장, REST GET /sameas·POST /sameas/decide(수동 확정). ecad 는 1(원장)·5(정규명 완전 일치 + refdes/part_number 토큰 겹침)·7(수동) 단계만 탄다.
- 빠진 것 — [심사 앱] ecad 가 끼면 pid_map·지문 단계를 건너뛰고 fuzzy 에서 뺀다. 품번 토큰만으로 잇는 단계와 풋프린트 bbox 지문 단계가 필요하다. [ECAD] refdes·품번·풋프린트 치수를 목록형으로 준다. [MCAD] 인스턴스 단위 refdes 를 준다(CROSS-02). 실물 MCAD 이름 <지정번호>_<품번> 은 refdes 와 글자가 달라 5단계가 서지 않는다. ecad 노드 0건·rr_sameas 0행이라 실행된 적이 없다. 조직 명명 규칙은 미결이다.
- 풀리는 도메인(13) — pcb · soc · mem · rf · passive · pwr · xd · mech · sim · rel · disp · cam · sh
- 메커니즘 — interface.cross_file_untrusted · mechanical.drop_stress · electrical.emi
- 질문 예 — ECAD 리비전에서 이동·추가·삭제된 부품 자리 위의 기구(쉴드캔·TIM·브래킷)는 무엇인가 / 낙하 해석 pid 의 최악 응력이 어느 refdes 의 값인가 / 쉴드캔 3D 파트와 SC 접두 풋프린트가 같은 캔인가
- 선행 — CROSS-02 · CROSS-07 · ECAD 카탈로그: 부품 배치 목록(refdes·품번·풋프린트·좌표)
- 근거 — HR/sameas.py:163-178,472,475,509,558-563,580-582 · HR/routes.py:1673,1698 · DB rr_sameas 0행·rr_ir_nodes 는 mcad 20건뿐 · PLAN:4760(§10 14a) · SF/docs/NX_EXPORT_GUIDE.md:14-22

#### CROSS-02 · MCAD 부품 바디의 인스턴스 단위 refdes·품번·실장면 키

**부분 · P0** · 내야 하는 쪽 mcad

- 돌려줘야 하는 것 — 파트 인스턴스마다 {path, refdes(보드 안에서 유일한 회로 지정번호), part_number, 소속 보드 파트 경로, pcb_side(top|bottom), source(sidecar|name)}.
- 지금 — identify_part·describe_part 가 이름에서 designator·part_number 를 뽑는다(describe_part 는 좌석이 부를 수 있다). 사이드카 extras 가 VP.* 값을 통과시킨다.
- 빠진 것 — [MCAD 내보내기 저널 + StepForge] 실물 이름의 앞머리 지정번호는 자리마다 유일하지 않다 — 같은 이름이 134자리에 있고 유일화 접미사(__2)만 다르다. 저널이 인스턴스별 회로 지정번호와 PCB_SIDE 를 사이드카에 싣고 StepForge 가 칸으로 내야 한다. [심사 어댑터] designator·part_number·tags·meta 를 읽는 코드가 없다(grep 0건). 품번 수준 키는 이미 있어 그 부분은 수집만 하면 된다.
- 풀리는 도메인(9) — pcb · passive · soc · mem · rf · sh · pwr · xd · mech
- 메커니즘 — interface.cross_file_untrusted · new:electrical.desense · new:sensor.mounting_stress_offset
- 질문 예 — MCAD 에 실린 칩 바디가 어느 refdes 인가(같은 품번이 여러 자리일 때) / IMU 바디에서 스크류 고정홀까지 거리를 좌표 변환 없이 잴 수 있는가
- 선행 — MCAD 카탈로그: 파트 식별·사이드카 수집
- 근거 — SF/core/partid.py:1-14,155-166 · SF/docs/NX_EXPORT_GUIDE.md:14-22,244 · SF/docs/SIDECAR_SPEC.md:90 · HR/adapters/mcad.py grep(designator|part_number|tags|meta|extras) 0건 · GW 도구 목록 identify_part·describe_part

#### CROSS-03 · CAD 파트 ↔ 해석 PID 계보 브리지와 낡음 판정(치수 지문 폴백 포함)

**부분 · P0** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — bridge 행 {step_file, source_name, source_path, pid, status(meshed|substituted|skipped|failed|shell), node_count, elem_count, worked_name}, 결속 {mesh_report.artifacts.kfile 파일명·sha256, spec_digest}, stale(bool·사유). 폴백용 해석 파트 size_sorted[3][mm]·volume[mm³].
- 지금 — 게이트웨이 part_mesh_map·mesh_report(좌석 읽기 목록), IR bridge 엣지 코드, same-as 2단계 pid_map·4단계 지문.
- 빠진 것 — [심사 어댑터] 응답 키 parts 를 rows 로 읽어 브리지가 0건이다(시험 픽스처도 rows 라 통과한다). limit 를 주지 않아 기본 100 에서 잘린다. mesh_report 를 부르지 않아 kfile_checked 가 False 고정이고 stale 이 늘 true 다. modelmeta 가 파트별 size 를 내지 않는데 bbox 에서 유도하지 않아 지문 단계도 서지 않는다. [MCAD] MCP 응답에 source_path 가 없다. 전부 데이터는 이미 있다.
- 풀리는 도메인(13) — sim · xd · mech · material · pwr · rf · disp · cam · rel · pcb · soc · mem · sh
- 메커니즘 — interface.tied · new:process.mesh_stale · mechanical.drop_stress · material.property_uncertain
- 질문 예 — K파일 PID 가 대상 리비전 CAD 파트와 1:1 대응하는가 / 메시가 갱신되지 않은 파트와 해석에서 빠진 파트는 무엇인가
- 선행 — MCAD 카탈로그: mesh_report 수집
- 근거 — HR/adapters/mcad.py:205,526 · DB rr_snapshot_calls part_mesh_map 2행 ok=1·contract_missing ['/rows']·응답 키 counts·parts(칸에 source_path 없음) · DB rr_ir_edges part_of 16·tied 8 · SF/app/mcp_server.py:2298,2323-2324 · KR/src/commands/modelmeta.cpp:953-962 · HR/adapters/dyna.py:282 · HR/sameas.py:475,509 · HWAXRisk/backend/tests/test_adapters.py:215

#### CROSS-04 · 리포트 ↔ K파일 ↔ STEP 리비전 결속 키

**부분 · P0** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — {report_id, source_kfile_id, kfile sha256, StepForge project_id·mesh job id·spec_digest, binding_method(declared|same_session|hash_match), 리포트 파트명과 K파일 title 의 불일치 비율[%]}.
- 지금 — report_summary 의 원본 K파일 링크, 리포트 목록의 kfile_id 필터, update_report_meta, mesh_report 의 artifacts.kfile. 어댑터는 사용자가 선언한 결속(user_declared)만 싣는다.
- 빠진 것 — [해석 + MCAD] StepForge 가 낸 덱과 DynaForge 에 올린 K파일을 잇는 공통 해시가 없어 파일명과 요소 수로만 대조된다. [심사 앱] 결속 강등 검문(report_parts_mismatch)이 없다. 다른 모델의 결과가 붙어도 드러나지 않는다.
- 풀리는 도메인(4) — sim · rel · xd · std
- 메커니즘 — new:process.mesh_stale · mechanical.drop_stress
- 질문 예 — 이 리포트가 이 리비전 형상으로 돌린 결과라는 것이 증명되는가
- 선행 — CROSS-03
- 근거 — HR/adapters/dyna.py:244-247(binding method user_declared) · GW list_tool_apps(heax-kooremapper_mcp: heaxkooremapper_mcp_list_reports kfile_id·update_report_meta 설명) · PLAN §2.13.4(행 검증 승계)

#### CROSS-05 · CAD 재질명 ↔ 물성 DB material_id 대응 원장

**부분 · P0** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — 과제의 재질명마다 {cad_material_name, material_id(정수), matched_name, match_basis(exact|normalized|manual), candidates_n, grade, manufacturer, decided_by}, 그리고 파트 → material_id.
- 지금 — StepForge material_lookup 이 materialtwin 출처일 때 evidence{material_id, matched_by}를 준다. 물성 DB 의 list_materials·find_materials_by_metadata.
- 빠진 것 — [MCAD] 라이브 스냅샷 part 12개 전부 재질이 null 이다. resolve_materials 는 evidence 를 버려 과제 단위 표에 id 가 없다. 사람이 적은 재질이 REST 캡처 채널에 안 실린다는 것은 앞 단계 소스 대조 결과다(이번에 재확인하지 않았다). [심사 앱] 대응 원장이 없고 정규화는 재질명 첫 토큰뿐이다. 이 키 하나가 비어 물성 DB 전체가 파트에 닿지 않는다.
- 풀리는 도메인(12) — material · mech · pwr · rf · disp · cam · sh · soc · mem · pcb · rel · sim
- 메커니즘 — material.property_uncertain · material.supplier_change · thermal.thermal_resistance · thermal.cte_mismatch
- 질문 예 — CAD 재질명이 물성 DB 의 어느 재료(id·등급·제조사)인가, 후보가 여럿인가 / 열경로 각 층의 열전도율을 층 두께와 묶을 수 있는가
- 선행 — MCAD 카탈로그: 재질 지정·해석 결과 수집
- 근거 — DB rr_ir_nodes part 12/12 재질 null · HR/sameas.py:699-716 · GW 도구 목록 material_lookup·resolve_materials · SF/core/materials.py:59-67,180-186(행 검증 승계)

#### CROSS-06 · PCB 스택업 자재 구분 → 자재 품번 → material_id 사상

**없음 · P1** · 내야 하는 쪽 join(ecad+other)

- 돌려줘야 하는 것 — {board_id, layer idx, material_class(CU|PPG|CCL|RCC|SR), grade/품번, material_id}.
- 지금 — 물성 DB 에 FR-4·프리프레그·CCL·동박 재료 행이 있다. cae00 표준 스택업이 층별 자재 구분까지 준다는 것은 문서 서술이다(unverified).
- 빠진 것 — [ECAD] 자재 등급·품번이 없다(구분 다섯뿐). [기타] 구분을 재료 id 로 잇는 표가 어디에도 없다. 우선순위는 행 최고값 P1 을 따랐다 — CTE·Tg 값 자체는 있고(OTH-01) 이 키만 빠져 있다.
- 풀리는 도메인(5) — pcb · material · rel · soc · mem
- 메커니즘 — thermal.cte_mismatch · process.warpage
- 질문 예 — 적층 자재가 리비전에서 바뀌었는가, 그 자재의 Tg·CTE·E 는 얼마인가
- 선행 — ECAD 카탈로그: 스택업 층 목록 · OTH-01
- 근거 — REF §3·§4.8·§4.17 · GW search_catalog_property 표본(행 검증 승계) · HR/sameas.py:699-716

#### CROSS-07 · 과제 ↔ 보드 잡 결속(다중 보드)과 보드 식별이 든 ECAD 키

**없음 · P0** · 내야 하는 쪽 join(ecad+심사 앱)

- 돌려줘야 하는 것 — 과제마다 boards[]{board_id(job_id), board_type(Main|Sub|S_AP|IF Sub|M_RF|interposer), revision, source_sha256, captured_at}, 노드 키 ecad:<board_id>:<refdes>, 보드 간 커넥터 핀 대응 {board_a·refdes·pin·net ↔ board_b·refdes·pin·net}.
- 지금 — ODB 잡 메타에 project·model·board_type·revision(사람 입력)이 있다. 계약은 '보드 1장 = 소스 1건' 이다.
- 빠진 것 — [심사 앱] 한 스냅샷에 kind 당 소스 1건만 싣고(첫 행만 쓴다) ECAD 키가 ecad:<refdes> 라 두 번째 보드를 싣지 못하고 실어도 refdes 가 충돌한다. [ECAD] 잡 메타와 보드 간 커넥터 넷 대응을 도구로 내야 한다. 원 행은 P1 이었으나 AP·메모리가 메인이 아닌 보드에 있는 과제는 스냅샷 자체가 서지 않으므로 ECAD 전 행의 선행 조건으로 보고 P0 로 올렸다.
- 풀리는 도메인(7) — pcb · soc · mem · pwr · rf · passive · xd
- 메커니즘 — electrical.net · new:interface.connector_retention · interface.cross_file_untrusted
- 질문 예 — 이 과제의 base/target 은 어느 보드 리비전들인가 / 충전 경로가 서브 보드·FPCB·메인 보드를 건너는 자리가 바뀌었는가
- 선행 — ECAD 카탈로그: 잡 목록·메타 · NF-02
- 근거 — PLAN:684(kind 당 최대 1건)·PLAN:56,719(ecad canon_key) · HR/adapters/registry.py:270,285 · HR/adapters/ecad_stub.py:13,29-41 · REF §3·§4.2·§4.12

### B 좌표 정합

#### CROSS-10 · 보드 좌표계 → 어셈블리 좌표계 변환 레코드와 확정 원장

**없음 · P0** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — 보드 1장마다 {transform_id, board_id, 회전 R[3×3] 또는 (rz[deg], 면 뒤집힘), 평행이동 t[mm], 면별 z 부호와 보드 상·하면 z[mm], anchors[3점 이상·한 줄 위 금지]{ecad 홀 x·y·지름[mm] ↔ mcad 보스/구멍 축점 xyz[mm]}, residual_rms_mm, residual_max_mm, 외곽 최대 편차[mm], basis(mounting_holes|outline|component_bodies|manual), 묶인 세대 키{mcad 보드 파트 형상 지문·파일 sha256, ecad job_id·source_sha256}, status(candidate|confirmed|stale), confirmed_by, confirmed_at}. 스냅샷마다 잔차를 다시 계산해 사람이 정한 한계를 넘으면 stale 로 내리고, 변환 자체를 diff 대상으로 둔다.
- 지금 — 재료만 있다 — MCAD align_frames(StepForge 과제 둘 사이 강체 변환·잔차), set_file_transform, fastener_report 축점, list_parts 월드 중심. ECAD 는 리포에 StepHeader datum 과 BOTHHOLE 좌표가 있고 cae00 get_mounting_holes 는 문서 근거다(unverified).
- 빠진 것 — [ECAD] 고정홀·컷아웃 목록과 외곽 폴리곤, 원점·datum 선언을 준다(원점은 과제마다 다를 수 있다고 문서가 적는다). [MCAD] 보드 파트 식별, 보스·구멍 축 좌표, 보드 상하면 z 를 준다. [심사 앱] 변환 추정 단계, 레코드·원장·화면·게이트, 세대 키 결속과 스냅샷별 재검증이 전부 없다(관련 코드 0건). 보드가 여럿이면 보드마다 따로 필요하다.
- 풀리는 도메인(13) — pcb · soc · mem · rf · pwr · passive · sh · disp · cam · mech · xd · sim · rel
- 메커니즘 — interface.cross_file_untrusted · interface.clearance · thermal.hotspot · new:electrical.antenna_detune · new:acoustic.port_alignment
- 질문 예 — 쉴드캔 상면 내측과 캔 안 최고 부품 상면 사이 간극은 얼마인가 / MEMS 마이크 PCB 음향 홀과 기구 포트의 정렬 편심은 얼마인가 / AP 발열원에서 배터리 셀·외곽 표면까지 최소거리는 얼마인가
- 선행 — CROSS-07 · NF-04 · ECAD 카탈로그: 고정홀·외곽 폴리곤 · MCAD 카탈로그: 체결·보스 축 좌표
- 근거 — HR grep(board_origin|coregist|board_transform|ecad_transform|board_frame|keep.?out) 0건 · GW align_frames 스키마(project_id·other_project_id 만) · GW search_tools('보드 좌표계를 어셈블리 좌표계로 변환 정합…') ECAD 정합 도구 없음 · PLAN:872(좌표 기준 설명 한 줄뿐) · REF:113 · HWAXRisk/docs/odb-adapter-contract.md(계약 조건 4)

#### CROSS-11 · ECAD↔MCAD 보드 판 일치 검문(refdes 단위 잔차표)

**없음 · P1** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — {대조한 odb job_id·MCAD 파일 해시, matched_ratio[0~1], refdes 별 dx·dy[mm]·drot[deg]·dheight[mm], only_in(ecad|mcad) 목록}.
- 지금 — 없음. ODB 쪽 리비전 비교(COMP-DIFF)는 ECAD 두 판 사이만 본다.
- 빠진 것 — [심사 앱] 변환 확정 뒤 MCAD 부품 바디와 ECAD 배치를 대조하는 계산이 없다. 기구에 얹힌 PBA 가 구판이면 join 수치가 전부 틀린 판 위에서 계산돼도 드러나지 않는다. 외곽·고정홀 잔차는 CROSS-10 의 산출로 넣었고, 이 행은 부품 바디가 실린 과제와 인스턴스 refdes 가 있어야 하므로 P1 로 두었다.
- 풀리는 도메인(4) — xd · pcb · mech · soc
- 메커니즘 — interface.cross_file_untrusted · interface.clearance_close
- 질문 예 — 기구 어셈블리에 얹힌 PBA 바디가 지금 심사하는 ODB 리비전과 같은 판인가, 어느 부품이 한쪽에서만 움직였나
- 선행 — CROSS-10 · CROSS-02 · ECAD 카탈로그: 부품 배치·높이 목록
- 근거 — HR/diff.py grep(ecad) 0건 · ODB/src/comparator/comparators/component_diff.py:11-93(앞 단계 조사 승계) · GW search_tools 정합 도구 없음

#### CROSS-12 · 해석 보드 모델 ↔ ECAD 리비전 정합 검문

**없음 · P1** · 내야 하는 쪽 join(sim+ecad)

- 돌려줘야 하는 것 — {보드 pid 두께[mm]·외곽 bbox[mm]·질량[g]·실장 부품 pid 수} 대 {ECAD 총두께[mm]·외곽·부품 수·체적 기반 질량[g]}, 항목별 차이[%], 낡음 플래그.
- 지금 — 정합 검문은 dyna↔mcad 뿐이다(R-006, G6 의 대각비).
- 빠진 것 — [심사 앱] ecad↔dyna 를 견주는 코드가 없다. 보드가 한 리비전 뒤처진 해석 결과가 붙어도 드러나지 않는다. [해석] 파트 두께·질량을 IR 에 실어야 한다(SIM-06).
- 풀리는 도메인(3) — sim · pcb · soc
- 메커니즘 — mechanical.drop_stress · mechanical.mass · new:process.mesh_stale
- 질문 예 — 해석 모델의 보드가 지금 ECAD 리비전과 같은 보드인가
- 선행 — CROSS-07 · SIM-06 · ECAD 카탈로그: 보드 두께·외곽·체적
- 근거 — HR/state.py:255-282(G6 는 mcad 단위·dyna/mcad 대각비·ecad 단위 변환 실패만) · HR/diff.py grep(ecad) 0건

### C 파생 교차 사실

#### CROSS-20 · 부품 상면 ↔ 마주 보는 기구의 Z 간극(부품 봉투 투영)

**없음 · P0** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — {board_id, refdes, top_z[mm], facing_part(mcad 경로), z_gap_nominal[mm], z_gap_worst[mm](height_max 와 공차 반영), xy_overlap_area[mm²], basis(mcad_body|ecad_projection), transform_id}.
- 지금 — MCAD 판에 부품 바디가 실려 있으면 axis_gap·clearance_field 가 MCAD 단독으로 답한다(좌석에는 닫혀 있고 스냅샷에 없다).
- 빠진 것 — [ECAD] 부품 높이(comp_height_max·min)와 풋프린트 외곽을 목록으로 준다(원천에는 있고 도구 응답에는 없다). [심사 앱] 변환(CROSS-10)·대응(CROSS-01)·계산이 없다. 부품 바디가 실린 과제에서는 대조용이고, 바디가 없거나 ECAD 가 MCAD 보다 앞선 과제에서는 유일한 길이다.
- 풀리는 도메인(10) — pcb · soc · mem · rf · passive · sh · disp · cam · xd · mech
- 메커니즘 — interface.clearance · interface.clearance_close · interface.tolerance_stackup · new:optical.crosstalk_airgap
- 질문 예 — AP 상면에서 쉴드캔 천장까지 Z 간극과 공차 최악값은 얼마이고 리비전에서 줄었는가 / 보드 위 최고 부품과 그 위 기구물 사이 남는 간극은 얼마인가 / 센서 상면과 커버 글라스 하면 사이 에어갭은 얼마인가
- 선행 — CROSS-10 · CROSS-01 · CROSS-33 · ECAD 카탈로그: 부품 높이·풋프린트
- 근거 — HR/adapters/ecad_stub.py:30-41 · HR/sameas.py:472-582 · GW 도구 목록 axis_gap·clearance_field · AS:644-650,2061-2105(axis_·clearance_ 접두 미허용) · ODB/src/services/volume_service.py:40-59(앞 단계 조사 승계) · SF/docs/NX_EXPORT_GUIDE.md:14-22

#### CROSS-21 · ECAD 부품 ↔ 지목 MCAD 파트의 3D 거리·방향(발열원↔셀·스킨, 센서↔자석, 노이즈원↔급전점, NTC↔감시 대상)

**없음 · P0** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — {refdes, mcad part, distance[mm], vector[dx,dy,dz][mm], 사이에 낀 파트 목록(층 순서), 같은 쉴드캔 구획 여부, basis}.
- 지금 — MCAD 안에서는 measure_distance·nearest_parts·part_location 이 있다(좌석 닫힘). 배터리·쉴드캔 등은 역할로 찾을 수 있다.
- 빠진 것 — [심사 앱] ECAD 부품을 어셈블리에 올려 거리를 내는 질의가 없다. [MCAD] 자석 역할이 온톨로지 16종에 없어 이름으로만 찾는다. [ECAD] 서미스터 분류가 없다. 새 기본기는 없고 CROSS-10·CROSS-01 과 부품 배치가 갖춰지면 따라 나오는 값이다.
- 풀리는 도메인(8) — pwr · sh · soc · mem · rf · passive · disp · cam
- 메커니즘 — thermal.hotspot · new:thermal.charging_heat · new:sensor.magnetic_interference · new:electrical.desense · new:thermal.sensor_placement
- 질문 예 — 차저 IC·PMIC·벅 인덕터에서 셀 표면·외장면까지 3D 거리는 얼마인가 / 지자기 센서·홀 IC 는 자석에서 얼마나 떨어졌나 / NTC 서미스터가 감시 대상에서 몇 mm 인가
- 선행 — CROSS-10 · CROSS-01 · ECAD 카탈로그: 부품 배치 목록
- 근거 — SF/core/data/part_ontology.yaml(roles 16종 — glass·frame·bracket·pcb·shield_can·tim·battery·fastener·cushion_adhesive·connector·ic_package·passive_chip·antenna·camera·speaker_mic·analysis_aid) · HR/sameas.py:558-563 · GW search_tools 정합 도구 없음

#### CROSS-22 · 패키지 코너 ↔ 고정홀·보스 거리, 지지 스팬 내 위치 비, 소자 자리의 굽힘 주방향

**부분 · P0** · 내야 하는 쪽 join(1차 값은 ecad 단독)

- 돌려줘야 하는 것 — {refdes, corner_id, nearest_hole|boss{id, distance_mm}, support_span_mm, position_in_span[0~1], dist_to_outline[mm], 굽힘축 각도[deg]와 소자 장축과의 사잇각[deg], basis(board_holes|mcad_supports|sim_strain_dir)}.
- 지금 — MCAD 근사 — fastener_distribution 의 체결 중심 간격, slenderness_check 의 무지지 스팬, fastener_report 축점(좌석 닫힘·미수집). ODB 리포에 BOTHHOLE 좌표와 외곽·패드 거리 함수가 있다(OSC 한정 규칙에서만 쓴다).
- 빠진 것 — [ECAD] 임의 refdes 의 코너↔고정홀·외곽 거리를 묻는 조회가 없다. 보드 고정홀만으로 되는 1차 값은 좌표 변환을 기다리지 말고 ECAD 쪽이 내야 한다. [join] 구멍 없는 지지(쉴드캔 벽·브래킷·리브)와 MCAD 스팬을 쓰려면 CROSS-10 이 필요하다. 굽힘 주방향을 정하는 규칙은 어디에도 없다. 좌석 계약상 암산 수치는 쓸 수 없다.
- 풀리는 도메인(7) — mech · sim · pcb · soc · mem · rel · passive
- 메커니즘 — new:mechanical.board_strain · mechanical.drop_stress · mechanical.bending · new:mechanical.mlcc_flex_crack
- 질문 예 — 대형 BGA 코너에서 가장 가까운 보스까지 거리와 스팬 내 위치 비는 얼마인가 / MLCC 장축이 보드 굽힘 주방향과 나란한 소자는 어느 것인가
- 선행 — ECAD 카탈로그: 고정홀 목록·패키지 코너 좌표 · CROSS-10
- 근거 — ODB/src/checklist/component_classifier.py:199 · ODB/src/checklist/geometry_utils/clearance.py:70,117 · GW 도구 목록 fastener_distribution·slenderness_check·fastener_report · HR/assets/seat-contract.v1.json(_common, 행 검증 승계) · REF §4.10

#### CROSS-24 · 하중점 직하 지지(커넥터 체결·키 누름·접점 스프링 자리의 뒷면 받침)

**없음 · P1** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — {refdes, load_dir, backside_gap[mm], nearest_support_dist[mm], span[mm], 스팬 내 MLCC·BGA refdes[]}.
- 지금 — 없음. 보드 전체의 무지지 스팬(slenderness_check)과 소자↔고정점 거리(CROSS-22)만 있다.
- 빠진 것 — [join] 조립·사용 하중이 실제로 걸리는 그 점의 반대면 지지를 보는 계산이 없다. dev 게이트웨이에 ECAD 도구가 없고 변환도 없다.
- 풀리는 도메인(4) — pcb · passive · soc · xd
- 메커니즘 — mechanical.bending · new:mechanical.board_strain · electrical.pad_lift
- 질문 예 — 커넥터 체결·키 누름이 보드를 미는 자리 뒷면에 받침이 있는가
- 선행 — CROSS-10 · CROSS-20
- 근거 — GW list_tool_apps(18앱에 ECAD 앱 없음) · HR grep(변환 코드 0건)

#### CROSS-25 · 안테나 클리어런스 — 방사체 투영 영역 안의 PCB 동박·GND 겹침과 방사체↔금속 거리

**없음 · P0** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — {antenna part, board_id, 투영 다각형[mm, 보드 좌표], 층별 겹친 동박 면적[mm²]·비율, 최근접 금속 파트와 거리[mm]}.
- 지금 — 없음. part_location 은 MCAD 안에서 PCB 기준 상대 위치만 낸다.
- 빠진 것 — [MCAD] 파트 외곽을 평면에 투영하는 도구가 없다. [ECAD] 층별 동박 형상은 파싱·보관하지만 영역 질의가 없다. [join] 변환이 없다. 동박·패드처럼 MCAD 에 없는 것은 이 길이 유일하다.
- 풀리는 도메인(2) — rf · xd
- 메커니즘 — new:electrical.antenna_detune · interface.cross_file_untrusted
- 질문 예 — 안테나 클리어런스 안에 PCB 동박·GND 플레인이 층별로 얼마나 들어와 있는가
- 선행 — CROSS-10 · OTH-12 · ECAD 카탈로그: 층별 동박 영역 질의
- 근거 — GW search_tools('project part outline onto plane…', 행 검증 승계) · ODB/src/models.py:273-375(앞 단계 조사 승계) · HR grep(변환 코드 0건)

#### CROSS-26 · 방사체 세그먼트의 중심선 길이와 급전·접지 접점의 세그먼트상 위치 비

**없음 · P1** · 내야 하는 쪽 join(주로 mcad)

- 돌려줘야 하는 것 — {segment part, centerline_length[mm], 양 끝 slit_width[mm], feed·ground refdes, s_feed/L[0~1], 리비전 간 Δ[mm]}.
- 지금 — 없음. bend_profile 은 굽힌 판의 두께·반경·각도·폭을 낼 뿐이다.
- 빠진 것 — [MCAD] 중심선 길이 추출이 없다(검색에 해당 도구가 없다). [join] 접점 좌표를 어셈블리로 옮길 변환이 없다. 공진 주파수를 정하는 전기 길이는 어느 행에도 없었다.
- 풀리는 도메인(1) — rf
- 메커니즘 — new:electrical.antenna_detune
- 질문 예 — 세그먼트 길이와 급전·접지 위치가 리비전에서 바뀌었나
- 선행 — CROSS-10 · MCAD 카탈로그: 중심선·슬릿 추출
- 근거 — GW search_tools('중심선 길이 centerline length 세그먼트…') 해당 도구 없음(axis_gap·bend_profile 등만)

#### CROSS-27 · 전기적 접지 그래프와 뜬 금속

**없음 · P1** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — {islands[]{parts[]}, floating_metal[]{part, nearest_grounded_part, gap_mm}, 접지 접점 수와 접점 간 최대 간격[mm]}.
- 지금 — 재료만 있다 — 기하 접촉 그래프(IR tied·touching 엣지, interface_graph)와 기계적 자유물체 점검(free_bodies·rigid_body_check).
- 빠진 것 — [MCAD] 도전성(재질)과 접촉면 절연 처리(아노다이징·테이프)를 사람이 적을 칸이 필요하다 — 기하 접촉을 도통으로 읽을 수 없다. [ECAD] 보드 GND 접점(접지 패드·클립 자리)을 준다. [심사 앱] 합치는 코드가 없다.
- 풀리는 도메인(2) — rf · rel
- 메커니즘 — new:electrical.ground_continuity · electrical.emi · new:electrical.antenna_detune
- 질문 예 — 프레임·미드플레이트·PCB GND 를 잇는 접지 접점의 개수와 접점 간 최대 간격은 얼마인가
- 선행 — CROSS-05 · CROSS-10 · ECAD 카탈로그: 넷별 패드
- 근거 — GW search_tools('접지 연속성…', 행 검증 승계) · HR/assets/taxonomy.v1.json(electrical.net·si_pi·emi·creepage·pad_lift 의 default_tools 빈 배열 — 직접 확인)

#### CROSS-28 · 접점·탄성 요소의 눌림량과 덮개를 밀어내는 반력 예산

**없음 · P1** · 내야 하는 쪽 join(mcad+사양)

- 돌려줘야 하는 것 — 접점마다 {refdes 또는 part, free_height_mm, working_range_mm, gap_to_contact_mm, compression_mm}, 덮개마다 {element 목록, 요소별 force[N], Σforce[N], 작용 중심 xy[mm], adhesive_band_area[mm²], 단위 면적 하중[N/mm²]}.
- 지금 — 압축량 원천은 게이트웨이에 있다(axis_gap 음수 간섭·clearance_field, 좌석 닫힘). DynaForge cclip op 은 눌린 상태의 덱을 만드는 잡이고 하중–변위는 사람이 넣는다.
- 빠진 것 — [기타] 작동 높이 범위와 하중–변위 곡선은 부품 사양서 값이라 어디에도 없다(OTH-08). [심사 앱] 요소별 반력을 합쳐 접착 유지력과 견주는 계산이 없다. 원 행(접점 눌림량)은 P2 였으나 합력으로 나는 들뜸을 보는 제안을 합쳐 P1 로 두었다.
- 풀리는 도메인(5) — rf · disp · xd · material · mech
- 메커니즘 — new:interface.contact_spring_stroke · material.adhesive_aging · material.creep · interface.touching
- 질문 예 — 급전·접지 C-clip 의 눌림량은 작동 범위 안인가 / 눌린 접점·스펀지·가스켓·TIM 의 반력 합이 접착 유지력을 넘는가
- 선행 — OTH-08 · CROSS-10 · OTH-01
- 근거 — GW list_operations·describe_operation('cclip')(행 검증 승계) · GW 도구 목록 axis_gap·clearance_field · HR/sameas.py:472-583

#### CROSS-29 · 노출 도체 ↔ 금속 기구·외장 틈의 3D 거리(연면·공간거리·ESD 방전 경로)

**없음 · P2** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — {net_name, 노출 패드·마스크 개구 위치, 최근접 금속 파트 또는 외장 틈, 공간거리[mm], 사이 절연물 유무}.
- 지금 — ODB 가 패드·솔더마스크 층 피처를 파싱한다. MCAD 에 틈 목록(leak_report)이 있다.
- 빠진 것 — [join] ECAD 도체 형상을 어셈블리 좌표에 올리는 경로가 없다. 택소노미상 electrical.creepage 는 검출 수단 미상이고 기본 도구가 없다. std 가 맡을 creepage·emi 기구는 이 행과 CROSS-27 이 받는다.
- 풀리는 도메인(3) — pwr · rel · std
- 메커니즘 — electrical.creepage · electrical.emi
- 질문 예 — VBUS 패드·배터리 탭과 금속 기구 사이 공간거리는 얼마이고 절연 테이프가 있는가
- 선행 — CROSS-10 · CROSS-05 · OTH-11
- 근거 — HR/assets/taxonomy.v1.json(electrical.creepage unknown·default_tools []) · HWAXRisk/docs/odb-adapter-contract.md(조건 5 — 패드·비아·트레이스는 계약 밖)

#### CROSS-30 · 보드 실장 부품 ↔ 하우징 개구·작동부 정렬(마이크 포트, USB·SIM·이어잭 개구, 사이드 키)

**없음 · P1** · 내야 하는 쪽 join

- 돌려줘야 하는 것 — {refdes, opening/key part, offset_x·offset_z[mm], perimeter_gap_min[mm], recess_depth[mm], backstop_gap[mm], plunger_to_actuator_gap[mm, 부호], key_travel_limit[mm], lateral_clearance 분포[mm]}.
- 지금 — 축방향 간극과 둘레 분포는 부품 바디가 실린 판에서 axis_gap·clearance_field 로 뽑을 수 있다(좌석 닫힘·미수집). 구멍 도구(corner_proximity·ligament_check)는 구멍 축선 기준이다.
- 빠진 것 — [MCAD] 비원형 개구의 중심·테두리 추출과 key 역할이 없다(역할 16종에 없다). [ECAD] 스위치 분류와 커넥터 입구면이 없다. [기타] 스위치 스트로크는 사양이다. [join] 변환이 없다. USB 삽입 하중과 키 눌림은 xd 좌석의 단골 지적인데 입력 행에 없었다.
- 풀리는 도메인(5) — sh · xd · pwr · rel · mech
- 메커니즘 — new:acoustic.port_alignment · interface.tolerance_stackup · electrical.pad_lift · mechanical.rattle
- 질문 예 — USB·SIM 소켓이 하우징 개구 중심에 오고 삽입 하중이 기구로 흐르는가 / 키를 눌렀을 때 스위치 작동 전후 여유와 키 둘레 유격이 얼마인가
- 선행 — CROSS-10 · CROSS-01 · OTH-08 · MCAD 카탈로그: 개구 추출
- 근거 — SF/app/mcp_server.py:11016-11030(corner_proximity 는 꼭짓점↔구멍 축선 거리) · SF/core/data/part_ontology.yaml(roles 16종에 key 없음) · HR grep(변환 코드 0건)

#### CROSS-32 · 해석 접촉 정의 ↔ CAD 계면 대조

**부분 · P0** · 내야 하는 쪽 join(sim+mcad)

- 돌려줘야 하는 것 — 접촉 쌍마다 {dyna contact(type·title·a·b), 대응 mcad 계면(kind·min_gap·band), 불일치 종류(해석에만 있음|CAD 에만 있음|종류 다름)}, 그리고 mesh_report 의 dropped_tied·unmatched_contacts.
- 지금 — 어댑터가 contact_edges·single_surface 를 contact 엣지로 싣고 규칙 R-006 이 대조한다. mesh_report 의 interface_diff 는 좌석이 읽을 수 있다.
- 빠진 것 — [심사 앱] dyna 캡처가 0건이고 mcad↔dyna 대응(CROSS-03)이 죽어 R-006 이 평가되지 않는다. 대조는 대응이 선 쌍에서만 의미가 있다.
- 풀리는 도메인(3) — sim · xd · rel
- 메커니즘 — interface.tied · interface.tied_loss · new:process.mesh_stale
- 질문 예 — 접촉 정의가 CAD 계면과 어긋나는 쌍은 어디인가
- 선행 — CROSS-03 · SIM-01
- 근거 — HR/assets/rules-seed.v1.json(R-001~R-007 일곱 개 — 직접 확인) · DB rr_sources 4행 전부 mcad · AS:644-650(mesh_report 읽기 목록) · HR/adapters/dyna.py:302-336(행 검증 승계)

#### CROSS-33 · 교차 파생 사실을 IR 엣지로 동결하고 변화 이벤트로 내기

**없음 · P0** · 내야 하는 쪽 other(심사 앱)

- 돌려줘야 하는 것 — 엣지 {a=ecad component nid, b=mcad part nid, z_gap_mm(부호), lateral_gap_mm, xy_overlap_area_mm2, height_basis(max|min), transform_id, confidence}, 이 엣지를 읽는 명명 치수 선택자, 간극 변화 이벤트(전·후 mm).
- 지금 — 엣지 종류에서 도메인을 가로지르는 것은 bridge 하나뿐이고 교차 이벤트는 cross.bridge_stale 하나다.
- 빠진 것 — [심사 앱] 계산 결과가 실시간 조회로만 있으면 '0.25 mm 가 0.12 mm 로 줄었다' 는 변화가 diff 에 나오지 않고 [e:]·[c:] 로 인용할 수 없다. interface.clearance_close 는 변화 자체가 기구이므로 동결이 없으면 좌석이 볼 것이 없다.
- 풀리는 도메인(8) — pcb · soc · mem · rf · sh · pwr · passive · xd
- 메커니즘 — interface.clearance_close · interface.clearance · interface.tolerance_stackup
- 질문 예 — 정합으로 얻은 부품 상면 간극을 리비전끼리 견줄 수 있는가
- 선행 — CROSS-20 · CROSS-21 · NF-02
- 근거 — HR/ir_builder.py:47-53(KIND_FAMILY) · HR/diff.py:1415-1420 · HR/diff.py grep(ecad) 0건

### D 해석·시험 결과

#### SIM-01 · 낙하 파트별 최악값·최악 방향·리비전 델타와 파트별 허용값 대비 비

**부분 · P0** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — parts[]{pid, 대응 mcad 파트, worst_stress{value[MPa], case_key}, worst_g, worst_disp[mm], min_safety_factor, 파트별 허용값(재료 카드 sigy 또는 물성 DB) 대비 비}, findings[]{severity, title, 귀속 파트·케이스}, worst_cases[]{case_key, identity(각도·위치)}, 리비전 델타(전·후·case_key).
- 지금 — 게이트웨이 report_part_risk·report_worst_cases·report_findings·compare_reports(좌석 통로 열림). 어댑터가 results.part_risk 와 pid 노드 오버레이를 싣고 diff 가 worst_stress·worst_g·worst_disp 를 견준다.
- 빠진 것 — [심사 앱] ① 실캡처가 0건이다. ② 브리지가 죽어 MCAD 파트에 귀속되지 않는다(CROSS-03). ③ results 에 sim_params 가 없어(해시만) over_yield 가 늘 미측정이고, 있어도 전 파트를 yield_stress 한 값으로 나누므로 파트별 허용값으로 바꿔야 한다. ④ report_worst_cases 에 limit 를 주는데 스키마 인자는 top_n 이다(영향 unverified). ⑤ 리포트 3건 중 첫 건만 읽고 min_safety_factor 는 diff 대상이 아니다. ⑥ findings 가 파트·케이스에 묶이지 않는다. have 로 적었던 세 행은 코드 경로만 있고 실데이터로 돈 적이 없어 partial 로 내렸다.
- 풀리는 도메인(13) — mech · sim · disp · cam · rel · sh · pcb · passive · soc · mem · pwr · rf · xd
- 메커니즘 — mechanical.drop_stress · mechanical.bending · interface.tied_loss
- 질문 예 — 윈도우·UTG·카메라 모듈의 최악 응력·G·변위는 얼마이고 어느 방향에서 나오며 base 대비 얼마나 변했나 / 파트별 최악 응력이 그 파트 재료의 항복 대비 몇 배인가
- 선행 — CROSS-03 · CROSS-04 · SIM-06
- 근거 — HR/adapters/dyna.py:26,155,202-217,230 · HR/state.py:535-549 · HR/diff.py:42,1144-1175 · GW report_worst_cases 스키마(top_n) · GW report_corpus(reports 0) · DB rr_sources 4행 전부 mcad · AS:644-650

#### SIM-02 · 방향 범주별·각도별 슬라이스와 케이스 지표(주응력·국부 충격 위치)

**도구는 있음 · 스냅샷 미수집 · P1** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — (case_key, 각도 또는 위치 F1~F6, part, 물리량(peak_stress|peak_principal|peak_strain|peak_vm_strain|peak_g|peak_disp), 값, at_time) 평탄 fact, 범주별(face|edge|corner) 최악값, 임팩터{type, mass, velocity, 에너지}.
- 지금 — report_directional·report_case·report_scatter(좌석 열림), report_query·report_angle_stats·report_geometry(좌석 닫힘).
- 빠진 것 — [심사 앱] 스냅샷에는 최악 5건의 방향과 파트별 최악 case_key 만 실린다. report_query·report_angle_stats 는 읽기 목록에 없어 좌석이 못 부른다. 임팩터 조건은 해시로만 남는다. impact 의 footprint 는 상류가 지어낸 사각형일 수 있어 위치 근거로 쓰면 안 된다.
- 풀리는 도메인(4) — disp · cam · sim · mech
- 메커니즘 — mechanical.drop_stress · new:mechanical.local_impact
- 질문 예 — 글라스의 방향별 최대 주응력은 얼마인가 / 펜드롭·볼드롭에서 접힘부·에지 위치별 패널 응답은 어떤가
- 선행 — SIM-01
- 근거 — GW report_query 스키마(metric 목록) · AS:644-650(report_query·report_angle_stats·report_geometry 없음) · HR/adapters/dyna.py:28,221-229 · KR/platform/backend/app/reports/parser.py:664-683

#### SIM-03 · 보드 위치별(패키지 코너·소자 자리) 변형률과 변형률 속도

**부분 · P0** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — {refdes 또는 (x,y)[mm, 보드 좌표], corner_id, 주변형률[µε], 주방향[deg], 변형률 속도[1/s], case_key, 출처(해석|변형률 게이지 시험)}.
- 지금 — 파트 단위는 있다 — report_query 의 peak_strain·peak_principal·peak_vm_strain(좌석 닫힘), report_part_series 의 파트 시계열과 report_scatter(좌석 열림). 파서가 파트별 peak_strain·peak_principal_strain 을 읽는다.
- 빠진 것 — [해석] 보드 좌표의 한 점으로 결과를 읽는 길이 없고 변형률 속도·조인트 박리 응력 칸이 없다. sphere 의 peak_strain 은 유효소성변형률이다. [심사 앱] 변형률 지표를 싣지 않는다. dev 에 리포트가 없어 실응답은 unverified 다. 현업의 1차 근거는 게이지 시험이므로 SIM-18 로도 받아야 한다. missing 으로 적은 행은 위치 단위를 가리킨 것이라 partial 로 합쳤다.
- 풀리는 도메인(7) — pcb · passive · soc · mem · mech · sim · rel
- 메커니즘 — new:mechanical.board_strain · electrical.pad_lift · new:mechanical.mlcc_flex_crack
- 질문 예 — BGA 코너 자리의 보드 변형률과 속도는 얼마인가 / MLCC 위치의 보드 굽힘 변형률이 크랙 한계에 얼마나 가까운가
- 선행 — SIM-01 · CROSS-01 · CROSS-10 · SIM-18
- 근거 — GW report_query 스키마 · KR/platform/backend/app/reports/parser.py:220-226,288-303 · AS:644-650 · HR/adapters/dyna.py:208-217 · GW report_corpus(reports 0)

#### SIM-04 · 해석 조건값·필수 시나리오 커버리지·결과 신뢰 지표

**부분 · P0** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — {kind, unit_system, drop_height[mm], doe_strategy, n_cases, 범주별 케이스 수, 미커버 방향, impactor mass·velocity, yield_stress}, 신뢰 지표{energy_ratio_min·max, has_mass_added, normal_termination, failed_runs, sphere_coverage}, 요구 대비 대조표.
- 지금 — report_summary 가 sim_params·doe_strategy·n_cases 를 준다(좌석 열림). 어댑터는 results.summary 와 sim_params_hash 만 남긴다. 요구 쪽은 scenario_coverage 신호가 있다.
- 빠진 것 — [심사 앱] results.summary 를 읽는 신호가 없고 조건값과 energy_balance 를 버린다. 시나리오 대조는 결과 kind(deep|sphere|impact) 해상도뿐이고 scenario_map 자산이 없어 높이·방향·코너가 요구와 이어지지 않는다. 물성 시험 조건과 맞세울 하중률 조건도 스냅샷에 없다.
- 풀리는 도메인(5) — sim · std · rel · material · xd
- 메커니즘 — mechanical.drop_stress · material.property_uncertain
- 질문 예 — 해석 조건이 필수 시나리오를 덮는가, 미커버 방향은 무엇인가 / 에너지 수지와 종료 상태로 보아 이 결과를 믿어도 되는가
- 선행 — SIM-01 · OTH-03
- 근거 — HR/adapters/dyna.py:28,202-207,401 · HR/requirements.py:372-407 · HR/assets/taxonomy.v1.json(scenario_map 키 없음 — 직접 확인) · KR/platform/backend/app/reports/parser.py:259-277,362-371,601-602

#### SIM-06 · 해석 파트 구성·재료 카드·질량·두께의 적재와 변경 감지

**부분 · P0** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — 파트마다 {pid, title, elem_class, n_elems, thickness[mm], mass, edge_len{min,p50,max}, material{mid, keyword, name, E, nu, rho, sigy, db{match_basis, db_mid, name, E_GPa, rho_g_cm3}}}, K파일 단위계 선언.
- 지금 — inspect_file 의 modelmeta.parts(좌석 읽기 목록)와 어댑터 pid 노드.
- 빠진 것 — [심사 앱] 재료를 kfile 아래 중첩 그대로 싣는데 diff 는 평평한 material.E·rho·sigy·nu 를 읽어 값 변경을 못 잡는다. thickness·mass·edge_len 은 싣지 않는다. [해석] K파일에 단위 선언이 없어 DB 단위(GPa·g/cm³)와 맞출 칸이 없다. dyna 캡처 0건이라 경로 전체가 미검증이다. 데이터는 이미 modelmeta 에 있다.
- 풀리는 도메인(4) — sim · material · passive · xd
- 메커니즘 — material.property_uncertain · mechanical.mass · mechanical.drop_stress
- 질문 예 — 해석 재료 카드(E·nu·rho·sigy)가 CAD 지정 재질·DB 값과 같은가 / 해석 덱에 수동 소자가 개별 pid 로 있는가, 집중질량으로 뭉쳤는가
- 선행 — CROSS-03 · CROSS-05
- 근거 — KR/src/commands/modelmeta.cpp:953-1008(thickness·mass·edge_len·material.kfile·db 출력 — 직접 확인) · HR/adapters/dyna.py:282-293 · HR/diff.py:947,1020-1034 · DB rr_sources 4행 전부 mcad

#### SIM-07 · 케이스별 접촉 쌍 하중·하중 경로·동적 간극 닫힘

**부분 · P1** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — {pair(CAD 파트 키), case_key, contact(bool), contact_force_peak[N], total_work, confidence, 전파 순서, static_gap[mm], min_dynamic_gap[mm], relative_disp_peak[mm], 시각[ms]}.
- 지금 — report_energy_flow 가 sphere·impact 에서 케이스별 접촉 엣지{src, dst, name, peak_force, total_work, confidence}를 준다(좌석 열림). 어댑터가 원문을 싣는다.
- 빠진 것 — [심사 앱] case_key 없이 불러 첫 케이스만 싣고(최악 케이스가 아니다) load_path 엣지를 만들지 않는다. [해석] 쌍의 최소 동적 간극과 상대 변위는 어느 도구도 내지 않는다. 제안은 missing 으로 보았으나 접촉력은 이미 있어 partial 이다.
- 풀리는 도메인(6) — mech · pwr · disp · cam · rel · sim
- 메커니즘 — interface.clearance_close · mechanical.drop_stress · new:mechanical.battery_puncture
- 질문 예 — 정적 간극이 낙하 중 상대 변위로 닫히는가, 닿는다면 얼마의 힘으로 닿는가 / 최악 케이스의 하중 경로는 무엇인가
- 선행 — SIM-01 · CROSS-03
- 근거 — GW report_energy_flow 스키마(case_key 선택 인자) · HR/adapters/dyna.py:238-242 · AS:644-650 · GW search_tools('두 파트 사이 동적 간극 상대 변위 접촉력…') 쌍 단위 결과 도구 없음

#### SIM-08 · 열충격 SED 예측과 입력 자동 채움

**도구는 있음 · 스냅샷 미수집 · P0** · 내야 하는 쪽 sim(입력은 ecad)

- 돌려줘야 하는 것 — 입력 {board_type(INT|HALF|FULL), ap_cx·ap_cy·pkg_cx·pkg_cy[mm], pkg_type(WLP|FX|DIG), pkg_x·pkg_y[mm], ball_size('지름/피치' µm), pad_size[µm]} → 출력 {sed_pred, judgement(>2.0 WARNING·>2.2 FAIL), uncertainty_std, out_of_range, model_version}.
- 지금 — predict_sed(좌석 유지 도구), sed_sample_from_odb(odb-hub 응답을 입력으로 바꾸는 변환기, 좌석 닫힘).
- 빠진 것 — [ECAD] 좌표·치수 6칸을 줄 도구가 dev 게이트웨이에 없다. [기타] pkg_type·ball_size·board_type 은 사람 몫이다(OTH-08). [심사 앱] 결과가 IR 에 안 실려 diff 에 나오지 않는다. 모델이 내는 것은 큰 패키지 옆 소형 패키지의 SED 이고 학습이 전부 POP 라 적용 범위를 함께 봐야 한다(행 검증 승계).
- 풀리는 도메인(6) — soc · mem · pcb · pwr · rel · passive
- 메커니즘 — thermal.thermal_shock · thermal.solder_fatigue
- 질문 예 — AP 와 이웃 소형 패키지의 열충격 SED 예측이 target 에서 기준(2.0·2.2)을 넘는가
- 선행 — ECAD 카탈로그: 부품 상세(좌표·패키지 치수·패드) · OTH-08 · SIM-20
- 근거 — GW predict_sed 스키마 · AS:662-666(_RISK_KEEP_TOOLS) · GW search_tools('ODB') 는 sed_sample_from_odb 뿐(앞 단계 조사 승계) · HR/assets/taxonomy.v1.json(thermal_shock·solder_fatigue default_tools [predict_sed])

#### SIM-09 · 보드 리플로우 휨 예측

**부분 · P1** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — 입력 {copper_imbalance_pct, stackup_asymmetry, board_thickness_mm, diagonal_mm, peak_temp_c} → 동적 휨[µm]과 민감도 곡선.
- 지금 — pcb_warpage_surrogate(좌석 유지 도구).
- 빠진 것 — [해석] 도구 설명이 합성 데이터로 학습한 데모이며 절대값을 판정 근거로 쓰지 말라고 적는다. 보드 전체 휨이지 패키지 하부 국부 휨이 아니다. [ECAD] 필수 입력 둘(동박 불균형·스택업 비대칭)의 산식이 없다. [심사 앱] 미수집이다.
- 풀리는 도메인(3) — pcb · soc · sim
- 메커니즘 — process.warpage
- 질문 예 — 리플로우 동적 휨 예측값이 base 대비 target 에서 얼마나 달라지는가
- 선행 — ECAD 카탈로그: 층별 동박률·스택업 대칭성 · SIM-20
- 근거 — GW pcb_warpage_surrogate 스키마·설명(합성 데이터 경고) · AS:662-666

#### SIM-10 · 패키지 온도별 휨 측정·공급사 데이터

**없음 · P1** · 내야 하는 쪽 other(측정 자료)

- 돌려줘야 하는 것 — {part_number, temperature[℃], warpage[µm, 부호 smile/cry], coplanarity[µm], PoP 상하 상대 휨[µm], 측정법}.
- 지금 — 없음. DynaForge warpage op 은 측정 변형을 덱에 입히는 실행 op 이다.
- 빠진 것 — [기타] 공급사 자료·시험 결과를 담는 표와 도구가 없다. 측정 자료이므로 side 를 sim 에서 other 로 옮겼고 근거 등급은 측정이다. 택소노미가 보드 휨과 패키지 휨을 process.warpage 한 코드로 묶는다.
- 풀리는 도메인(3) — soc · mem · pcb
- 메커니즘 — process.warpage · new:process.package_warpage · process.solder
- 질문 예 — PoP 상·하 패키지의 리플로우 온도별 휨이 보드 국부 휨과 합쳐져 볼 높이 여유 안에 드는가
- 선행 — OTH-06 · OTH-08 · NF-07
- 근거 — GW list_operations(warpage, 행 검증 승계) · HR/assets/taxonomy.v1.json(process.warpage 단일 코드 — 직접 확인)

#### SIM-11 · 열 결과 — 접합·표면·스킨 온도(해석 또는 측정)

**없음 · P1** · 내야 하는 쪽 sim(또는 시험)

- 돌려줘야 하는 것 — {refdes 또는 part, 시나리오, Tj[℃], 표면·스킨 온도[℃], Rth[K/W], 주변 온도[℃], 출처(해석|측정)}.
- 지금 — 없음. 리포트 종류는 낙하·충격 셋뿐이고 SED·휨 대리모델은 온도 분포가 아니다.
- 빠진 것 — [해석·시험] 열 결과를 만들거나 반입하는 경로가 없다. 스킨 온도는 현업에서 시험 측정이 1차 근거이므로 SIM-18 로도 받는다. 과거 열해석 보고서가 아카이브에 문서로 있는지는 unverified 다.
- 풀리는 도메인(6) — soc · pwr · mem · disp · cam · sim
- 메커니즘 — thermal.hotspot · thermal.thermal_resistance · new:thermal.skin_temperature
- 질문 예 — 발열원 아래(옆) 패널 배면과 카메라 모듈 자리의 온도는 얼마인가 / 충전 중 셀 표면과 외장 스킨 온도는 얼마인가
- 선행 — SIM-20 · SIM-18 · OTH-07
- 근거 — GW search_tools('열해석 온도 분포 접합온도 스킨 온도…') 열 결과 도구 없음 · HR/assets/taxonomy.v1.json(thermal.hotspot default_tools [], thermal.thermal_resistance unknown) · PLAN:4853(§10 B-31)

#### SIM-12 · 전자기 결과 — 효율·공진·격리도·SAR·OTA(해석 또는 측정)

**없음 · P1** · 내야 하는 쪽 sim(또는 시험)

- 돌려줘야 하는 것 — {antenna, band, efficiency[dB], resonance[MHz], isolation[dB], sar_1g[W/kg], TRP·TIS, 조건}.
- 지금 — 없음.
- 빠진 것 — [해석·시험] 전자기 해석·SAR·S-파라미터·OTA 측정을 읽는 도구가 없다. 형상 근거는 디튠 방향까지만 말하고 크기는 해석이나 측정이 있어야 한다.
- 풀리는 도메인(1) — rf
- 메커니즘 — new:electrical.sar · new:electrical.antenna_detune · new:electrical.antenna_isolation
- 질문 예 — 이 리비전의 안테나 효율·SAR 결과가 있는가
- 선행 — SIM-20 · SIM-18 · OTH-12
- 근거 — GW search_tools('클럭 주파수 고조파… EM SAR antenna efficiency') EM 도구 없음 · GW list_tool_apps(18앱에 EM 앱 없음)

#### SIM-13 · 모달·정적 굽힘·비틀림·압점 결과

**없음 · P1** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — modes[]{freq_hz, participating_parts[]}, 하중 케이스{3점·4점 굽힘 스팬[mm]·하중[N], 비틀림[N·m], 압점 위치·하중[N]}별 {세트 굽힘 강성[N/mm], 비틀림 강성[N·m/deg], 파트별 최대 주응력[MPa]·주변형률, 배면 접촉 여부·하중[N]}.
- 지금 — DynaForge modal op 은 덱을 고유치 해석용으로 바꾸는 변환이다. laminate 의 compute_natural_frequencies 는 균질 패널용이고 백엔드가 내려가 있다.
- 빠진 것 — [해석] 해석 통로가 낙하·충격뿐이고 모달·정적 결과를 읽는 리포트 종류가 없다. 택소노미는 mechanical.bending 의 기본 도구를 report_part_risk 로 적지만 그 도구는 낙하 결과만 준다.
- 풀리는 도메인(6) — sh · passive · rel · sim · mech · pcb
- 메커니즘 — mechanical.vibration · mechanical.bending · new:acoustic.mlcc_singing
- 질문 예 — LRA 구동 주파수와 장착 판의 구조 모드가 분리되는가 / 세트를 굽히고 비틀고 눌렀을 때 강성과 디스플레이 배면 접촉은 어떤가
- 선행 — SIM-20
- 근거 — GW search_tools('모달 해석 결과 고유진동수…')·('정적 굽힘 비틀림 압점 해석 결과…') 결과 판독 도구 없음 · HR/assets/taxonomy.v1.json(vibration·buckling default_tools [], bending [report_part_risk]) · LaminateAnalyzerMCP/app/mcp_server.py:245-246

#### SIM-14 · 적층 중립축·굽힘강성과 접힘 반경에서의 층별 굽힘 변형률

**부분 · P1** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — {neutral_axis_z[mm], EI[N·mm²], 층별{이름, 두께[mm], E, 중립축까지 거리[mm], 굽힘 변형률[%] at R}}.
- 지금 — mesh_stack_diagram 이 K파일 적층의 중립축·기하 중심면·굽힘강성을 텍스트로 준다. StepForge bend_profile 이 두께·반경을 준다.
- 빠진 것 — [해석] 메시 세션이 있어야 하고 감긴·접힌 적층은 거절하며 그림 산출물을 만든다. 층별 변형률을 내는 도구는 없다. [심사 앱] mesh_ 접두는 좌석에 닫혀 있고 미수집이다. Laminate Analyzer 는 오늘 backend_down(도구 0)이라 have_not_ingested 로 적은 행을 partial 로 맞췄다.
- 풀리는 도메인(3) — disp · mech · sim
- 메커니즘 — new:mechanical.fold_crease_strain · mechanical.fatigue
- 질문 예 — 접힘 시 적층 중립면이 어디이고 TFE·터치 메시 층이 얼마나 떨어져 있나
- 선행 — SIM-15 · OTH-01
- 근거 — GW list_tool_apps(heax-kooremapper_mcp: mesh_stack_diagram 설명) · GW list_tool_apps(heax-laminate_analyzer_mcp tool_count 0·backend_down) · AS:644-650,2061-2105

#### SIM-15 · 좌굴 임계하중과 적층 등가 강성(ABD) 계산

**리포에 있음 · 미노출 · P1** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — 입력 {Lx·Ly[mm], 경계 코드, 층별 두께[mm]·E[GPa]·ν} → {N_cr[N/mm], 여유 배수, ABD 행렬, 중립면 위치[mm]}.
- 지금 — LaminateAnalyzerMCP 리포에 compute_buckling·compute_abd_matrix·compute_neutral_axis·check_design_rules·get_reference_cases 가 있다.
- 빠진 것 — [해석] 게이트웨이에서 백엔드가 내려가 도구가 0개다. 좌석 유지 목록에 check_design_rules·get_reference_cases 가 적혀 있지만 지금은 부를 수 없다. 백엔드 복구만으로 노출된다. 입력(무지지 스팬·층 두께)은 MCAD 에서 와야 한다.
- 풀리는 도메인(5) — mech · sim · pcb · std · rel
- 메커니즘 — mechanical.buckling · mechanical.bending · process.warpage
- 질문 예 — 이 얇은 판·쉴드캔 천장·보드가 압축에서 좌굴하기까지 여유가 몇 배인가
- 선행 — MCAD 카탈로그: 무지지 스팬·적층 두께
- 근거 — LaminateAnalyzerMCP/app/mcp_server.py:68,77,212,223,653 · GW list_tool_apps(backend_down·tool_count 0) · AS:662-666 · GW search_tools('좌굴 임계하중…') 는 mesh_stack_diagram 만

#### SIM-17 · 세트 조립 상태의 배터리 스웰링 팽창 결과

**부분 · P1** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — {두께 증가[mm], 상대 파트 접촉 면압[MPa], 디스플레이·백커버 변위[mm], 입력 SOC·층별 팽창 변형률}.
- 지금 — DynaForge battery op(mode swell 포함)이 셀 단품 덱을 만든다.
- 빠진 것 — [해석] 덱 생성까지만 있고 세트 조립 스웰링 해석과 결과 판독이 없다. [심사 앱] 결과층 조건 키가 낙하·충격용 여섯뿐이라 읽을 자리가 없다.
- 풀리는 도메인(2) — pwr · disp
- 메커니즘 — new:mechanical.battery_swelling_clearance
- 질문 예 — 셀이 수명말에 닿은 뒤 얼마의 힘으로 디스플레이를 미는가
- 선행 — SIM-20 · OTH-03
- 근거 — HR/adapters/dyna.py:28 · GW describe_operation('battery')(행 검증 승계)

#### SIM-18 · 시험·측정 결과 적재 통로(시험 실행을 과제·부품·해석 케이스에 연결)

**부분 · P1** · 내야 하는 쪽 sim(시험)

- 돌려줘야 하는 것 — {test_run id, 과제·부품 키, 시험 종류, 조건(높이·사이클·온도·대역), 지표와 단위(변형률 µε, 온도 ℃, SAR W/kg, TRP dBm 등 표 형태), 합격 여부, 대응 해석 case_key, 측정 대 해석 차이}.
- 지금 — 보고서 아카이브에 test_run(시험일자·결과·측정값 숫자 1개·조건)·incident 객체와 tested·caused_by 관계가 있고 좌석이 search_objects·get_object·get_subgraph 로 읽는다.
- 빠진 것 — [기타] 측정값 칸이 숫자 하나라 위치별·대역별 표를 못 담고 해석 케이스와 잇는 칸이 없다. dev 아카이브는 시험·불량 객체가 0건이다(행 검증 승계). [심사 앱] 스냅샷에 실리지 않는다. 계획이 미결 항목으로 적어 둔 것이다.
- 풀리는 도메인(7) — rel · rf · sim · pcb · soc · pwr · std
- 메커니즘 — new:mechanical.board_strain · new:electrical.sar · mechanical.drop_stress
- 질문 예 — 해석값과 실측의 차이는 얼마인가 / 이 리비전의 OTA·디센스·SAR 시험 결과가 있는가
- 선행 — SIM-20 · OTH-16
- 근거 — GW list_object_types(test_run 속성 4개·incident·cae_part — 직접 확인) · AS:662-666 · PLAN:4852(§10 B-30 test_result 소스 제안)

#### SIM-19 · 보고서 아카이브의 해석 런 저장소를 결과 원천으로 쓰는 통로

**도구는 있음 · 스냅샷 미수집 · P1** · 내야 하는 쪽 sim

- 돌려줘야 하는 것 — {run_id, workflow(full_angle_drop|partial_impact|deep_report), project, status, quality_failed, peaks{part_key, quantity(stress|strain|g|disp), value, unit, axis}, findings, part_key ↔ 온톨로지 부품 id}.
- 지금 — list_analysis_runs·get_analysis_summary·get_analysis_peaks·list_analysis_parts 가 게이트웨이에 있고 해석 부품을 사내 부품에 잇는 same_as 관계가 온톨로지에 있다.
- 빠진 것 — [심사 앱] 좌석 유지 목록 15종에 없어 앱 좁힘에서 잘리고 어댑터도 읽지 않는다. dev 는 런 0건이다. 불량 객체와 파트를 잇는 다리가 되므로 유지 목록에 넣는 것만으로 열린다.
- 풀리는 도메인(2) — sim · rel
- 메커니즘 — mechanical.drop_stress
- 질문 예 — 아카이브에 적재된 해석 런에서 부품별 피크와 품질 경고를 읽을 수 있는가
- 선행 — CROSS-01
- 근거 — GW search_tools('해석 런 부품별 피크…')(list_analysis_parts·get_analysis_peaks·get_analysis_summary) · GW list_analysis_runs(total 0) · GW list_object_types(cae_part·same_as) · AS:662-666,3134-3139

#### SIM-20 · 낙하 외 물리 결과를 싣는 결과층과 지표 집합

**없음 · P0** · 내야 하는 쪽 other(심사 앱)

- 돌려줘야 하는 것 — 결과 행 {physics(thermal|static_bend|torsion|modal|em|warpage|sed|swelling|measured), case_key(하중·경계·모델 리비전), 귀속 노드(part·pid·component), 지표·단위, out_of_range·uncertainty_std, 한계 대비 여유, 근거 등급(도구예측|측정)}.
- 지금 — 결과층은 낙하·충격 리포트 전용이다 — 지표 3종, 조건 키 6종.
- 빠진 것 — [심사 앱] 열·휨·SED 가 핵심인 soc·mem·pcb·pwr 좌석은 도구가 살아 있어도 스냅샷에 남는 근거가 0이다. 계획이 미결 결손으로 적어 둔 항목이다.
- 풀리는 도메인(9) — soc · mem · pcb · pwr · rf · sh · sim · mech · rel
- 메커니즘 — thermal.hotspot · thermal.thermal_shock · process.warpage · mechanical.vibration · mechanical.bending
- 질문 예 — SED·열·휨 예측값의 리비전 간 변화를 diff 에서 볼 수 있는가
- 근거 — HR/diff.py:42 · HR/adapters/dyna.py:28 · HR/ir_builder.py:45 · PLAN:4853(§10 B-31)

### E 재료·사양·요구

#### OTH-01 · 재료 물성 조회·비교(조건·불확도·근거 등급·출처 포함)

**있음 · P0** · 내야 하는 쪽 other

- 돌려줘야 하는 것 — 물성값마다 {value, unit(SI), conditions{temperature, strain_rate, humidity, direction, frequency, substrate, test_standard}, uncertainty, quality_tier(1 측정…5 추정), method, source{doi, url}}, 재료 2~12종 나란히 비교, 시험 곡선·구성식 피팅·재료 카드.
- 지금 — heax-materialtwin_web 34도구. get_material·get_material_properties·compare_materials·search_catalog_property 등 18종이 앱 제한과 무관하게 좌석에 항상 묶인다. 열전도율 1,068건을 이번에 확인했고 CTE·Tg·유전율·접착·흡습·자기·솔더 상수 건수는 앞 단계 검증값이다.
- 빠진 것 — [심사 앱] 스냅샷에 실리지 않아 tool:panel 인용으로만 남고 리비전 diff 에 나오지 않는다. 좌석 예산이 3회라 물성 많은 재료는 도메인으로 좁혀야 한다. get_fits 는 유지 목록 밖이다. 값이 있어도 파트 재질명이 비어 조회 키가 없다(CROSS-05·CROSS-06).
- 풀리는 도메인(10) — material · disp · pcb · soc · mem · rf · sh · rel · mech · pwr
- 메커니즘 — material.property_uncertain · material.supplier_change · thermal.cte_mismatch · material.adhesive_aging · material.moisture · thermal.solder_fatigue
- 질문 예 — 교체 전후 재질의 E·CTE·Tg 차이는 얼마이고 같은 시험 조건·근거 등급에서 온 값인가 / 물성 시험 조건이 이 과제 하중 조건과 겹치는가
- 선행 — CROSS-05 · CROSS-06
- 근거 — GW list_tool_apps(heax-materialtwin_web 34도구·status ok) · GW search_catalog_property('thermal.conductivity') count 1068(조건·등급·출처 칸 실재) · AS:2093-2101 · HR/planner.py:23-24

#### OTH-02 · 장기·특수 물성 커버리지(크리프·압축영구줄음·갈바닉·유리 강화·음향 메시·근적외 투과·압축 대 접촉저항)

**부분 · P1** · 내야 하는 쪽 other

- 돌려줘야 하는 것 — creep_compliance[1/Pa]·compression_set[%]·완화 곡선 E(t), galvanic_potential[V]{전해질·기준전극}, surface_compressive_stress[Pa]·depth_of_layer[m]·weibull_modulus, 메시 비음향저항[Pa·s/m]·수압 한계[Pa], transmittance{wavelength_nm}, compression_pct ↔ contact_resistance, 폼 압축 반력 곡선.
- 지금 — 같은 물성 DB 도구. 키 정의는 있고 값이 드물다(앞 단계 검증값 — 크리프 12·압축영구줄음 8·갈바닉 43·CS 10·DOL 11·와이블 14·걸리 투기도 1건).
- 빠진 것 — [기타] 인공 땀 조건 갈바닉 값, 아노다이징·Ni/Au 도금 값, 메시 비음향저항과 수압 한계 키, 압축–저항 곡선 키가 없다. 근적외 조건 투과율과 폼 반력 곡선 보유는 unverified 다. 공백은 measurement_gaps·test_plan_for_material 로 진술하게 된다.
- 풀리는 도메인(7) — material · sh · mech · rf · disp · rel · std
- 메커니즘 — material.creep · material.corrosion · new:material.galvanic_pair · new:acoustic.mesh_membrane · electrical.emi
- 질문 예 — 이종 금속 접촉 쌍의 전위차는 얼마인가 / 가스켓 압축률에서 접지가 유지되는가 / 커버 글라스의 강화 사양과 강도 분포 근거는 무엇인가
- 선행 — OTH-01 · CROSS-05
- 근거 — GW search_catalog_property·list_property_definitions(앞 단계 검증 승계) · AS:2093-2101

#### OTH-03 · 과제 요구·판정 기준 원장(치수 한계·시나리오 조건값·규격·환경·비치수 한계)

**부분 · P0** · 내야 하는 쪽 other(심사 앱 + 사람)

- 돌려줘야 하는 것 — 요구 행 {kind, name, op(lte|gte|between), value, unit, 조건{낙하 높이[mm]·방향·횟수, 온도 범위[℃]·습도[%]·사이클 수·시간[h], 접힘 횟수·최소 곡률반경}, 대상 키(치수 이름|refdes|넷|파트), source_ref, status}, 그리고 충족 여유와 커버리지.
- 지금 — rr_requirements(kind dim_limit|scenario|standard)와 REST 조회·등록·승계, req: 인용, sig:req.margin·req.scenario_coverage·req.standards, 규칙 R-007.
- 빠진 것 — [심사 앱] ① 0행이다. ② kind 가 셋뿐이고 여유는 dim_limit 을 명명 치수와 대조할 때만 계산된다 — 전류·온도·수명·SAR·허용 G·스트레인 한계는 등록해도 대조 대상이 없어 판정이 좌석 경험으로 남는다. ③ dim_limit 은 rr_dim_vocab 에 이름이 있어야 등록되는데 그 표도 0행이다. ④ scenario 값은 {taxonomy_key, required}뿐이다. ⑤ 요구를 읽거나 넣는 게이트웨이 도구가 없다(REST 뿐). 흩어져 있던 요구 행을 하나의 엔진 항목으로 묶었다.
- 풀리는 도메인(15) — xd · sim · cam · rel · soc · disp · mech · pcb · rf · passive · pwr · sh · mem · std · material
- 메커니즘 — interface.tolerance_stackup · mechanical.drop_stress · thermal.thermal_shock · mechanical.fatigue · thermal.cte_mismatch
- 질문 예 — 바뀐 치수가 등록된 요구 한계와 얼마의 여유를 갖는가 / 필수 낙하·시험 시나리오 중 결과가 없는 것은 무엇인가 / 적용 규격이 이 과제 요구로 등록돼 있는가
- 선행 — OTH-04 · OTH-06 · SIM-04
- 근거 — HR/requirements.py:32,124,331-344,372-407 · HR/risk_store.py:47-61 · HR/routes.py:1411,1420,1431,1452 · DB rr_requirements 0·rr_dim_vocab 0·rr_dim_defs 0 · GW list_tool_apps(heax-hwax_risk 14종에 요구 도구 없음)

#### OTH-04 · 명명 치수와 공차 체인 누적(worst-case·RSS)

**부분 · P0** · 내야 하는 쪽 other(mcad + 심사 앱)

- 돌려줘야 하는 것 — chain[]{dim_name, nominal_mm, tol_minus, tol_plus, 분포 또는 Cpk, sign}, result{worst_min_mm, rss_min_mm, margin_mm}, 치수별 리비전 간 값.
- 지금 — StepForge 치수 기록부 — record_dimension 이 nominal·tol_minus·tol_plus 를 받고 compare_dimension·compare_projects 가 띠 판정을 낸다(읽기 둘은 좌석 열림). 심사 앱 rr_dim_defs 는 node·edge·result·const·dim(a)±dim(b)·sum|min|max 문법을 갖는다.
- 빠진 것 — [심사 앱] 정의 0행이다. 공차 칸이 없고(rr_dim_vocab.tol_abs·tol_rel 은 변경 임계다) 파생은 사칙 이항이라 중첩으로 worst-case 는 적을 수 있어도 제곱근이 없어 RSS 를 못 낸다. 부호 규약·기여도 표기가 없다. StepForge 기록부를 어댑터가 읽지 않는다. [MCAD] 도면 공차(PMI·GD&T)는 읽지 않고 기록 가능 도구가 일곱이라 공동 체적·틈 분포 칸이 없다.
- 풀리는 도메인(7) — mech · xd · pwr · sh · disp · cam · std
- 메커니즘 — interface.tolerance_stackup · process.tolerance
- 질문 예 — Z 스택 체인의 worst-case·RSS 여유는 얼마인가 / 셀 두께·포켓 깊이·테이프 공차를 넣었을 때 최악 스웰링 갭은 얼마인가
- 선행 — OTH-05 · OTH-03
- 근거 — HR/ir_builder.py:574-582,665,735-768 · HR/risk_store.py:177-188 · HR/routes.py:1362-1374 · GW search_tools 결과의 record_dimension 인자(nominal·tol_minus·tol_plus)·compare_dimension 설명(읽기 전용) · SF/core/dimensions.py:104 · PLAN:4865

#### OTH-05 · 빌드 실측 치수와 공정 능력

**없음 · P1** · 내야 하는 쪽 other(공정 자료)

- 돌려줘야 하는 것 — {dim name, build 단계, n, mean[mm], sigma[mm], min·max[mm], Cpk, 측정 방법, 시료 리비전}.
- 지금 — 없음.
- 빠진 것 — [기타] 명명 치수에 빌드별 실측을 잇는 입력 채널이 없다. 공차 체인의 분포 칸을 채울 유일한 근거이고 등급이 측정이 된다. 아카이브 시험 객체로 우회 가능한지는 unverified 다.
- 풀리는 도메인(4) — xd · mech · rel · disp
- 메커니즘 — interface.tolerance_stackup · process.tolerance
- 질문 예 — 이전 빌드에서 이 치수는 실제로 얼마나 흩어졌나
- 선행 — OTH-04 · OTH-06
- 근거 — GW search_tools('실측 치수 Cpk 공정 능력…') 해당 도구 없음(치수 기록부 도구만) · PLAN grep(cpk|moldflow|고조파|keep-out) 0건 · HR/requirements.py:32

#### OTH-06 · 과제 사실 원장 — 사람이 주는 설계 사실의 표 입력 채널

**부분 · P0** · 내야 하는 쪽 other(심사 앱)

- 돌려줘야 하는 것 — 사실 행 {kind(power_map|cell_spec|rail_condition|rf_band_map|underfill_plan|torque_spec|process_spec|package_spec|env_profile|measured_dim), 대상 키(board_id+refdes|파트 ckey|넷 이름|계면), 값·단위, 시나리오, source_ref, status(candidate|confirmed), 동결 해시, 인용 스킴}.
- 지금 — 일반 통로 셋 — 명명 치수 const:<숫자>(이름·단위·[d:] 인용·diff), rr_requirements 3종, StepForge set_part_metadata 의 tags·meta·note 와 사이드카 extras.
- 빠진 것 — [심사 앱] 소스 종류가 넷뿐이고 인용 스킴 18종에 사실을 가리킬 것이 없다. const: 는 숫자 하나라 대상 키 결속·시나리오 축·출처 칸이 없고 0행이다. StepForge 자유 항목은 어댑터가 읽지 않는다. 아래 OTH-07~OTH-13 이 전달돼도 담을 자리가 없어 질문 문자열로만 들어가고 좌석 계약은 인용 없는 수치를 경험칙으로 내린다.
- 풀리는 도메인(11) — soc · mem · pwr · rf · pcb · passive · mech · material · sim · sh · rel
- 메커니즘 — thermal.hotspot · electrical.si_pi · process.screw_torque · thermal.solder_fatigue
- 질문 예 — 사람이 준 소비전력·셀 사양·대역 매핑을 좌석이 인용하고 리비전끼리 견줄 수 있는가
- 선행 — CROSS-01 · CROSS-07
- 근거 — HR/ir_builder.py:45,574,665 · HR/common.py:130-133 · HR/requirements.py:32 · HR/adapters/mcad.py grep(tags|meta|extras) 0건 · SF/docs/SIDECAR_SPEC.md:90

#### OTH-07 · 부품별 소비전력(파워맵)과 동작 시나리오

**없음 · P0** · 내야 하는 쪽 other(회로·시스템 자료)

- 돌려줘야 하는 것 — {board_id, refdes, 시나리오(게임·촬영·유선 급속·무선·통신), power[W], duty, Tj_max[℃], 리비전 간 변화}.
- 지금 — 값은 어디에도 없다. ODB 부품 속성의 POW_TYP 는 수동소자 정격이다. 담을 일반 통로는 OTH-06 이다.
- 빠진 것 — [기타] CAD 어디에서도 유도되지 않아 회로·시스템 담당이 준다. 열전도율은 물성 DB 에 있으므로(OTH-01) 없는 것은 전력뿐이다. partial 로 적은 행은 일반 통로를 가리킨 것이라 값 기준으로 missing 으로 맞췄다.
- 풀리는 도메인(9) — soc · mem · pwr · mech · sim · rf · disp · cam · passive
- 메커니즘 — thermal.hotspot · thermal.thermal_resistance · new:thermal.charging_heat · new:thermal.skin_temperature
- 질문 예 — AP·PMIC·모뎀·충전 IC 의 소비전력과 같은 쉴드캔 구획 안의 동시 발열 조합은 무엇인가
- 선행 — OTH-06 · CROSS-01
- 근거 — ODB/src·api grep(underfill|watt|dissipation|소비전력|keepout) 0건 · GW search_tools('부품 데이터시트 사양… 소비전력 파워맵…') 해당 도구 없음 · PLAN:4853

#### OTH-08 · 패키지·부품 사양(품번 조회)

**없음 · P0** · 내야 하는 쪽 other(부품 승인원·데이터시트)

- 돌려줘야 하는 것 — 품번마다 {pkg_type(FC-CSP|FCBGA|PoP|FO-WLP|WLP|uMCP|UFS), ball_dia·ball_pitch[µm], body_thickness[mm], standoff[µm], PoP 구성, 볼 합금, MSL, Tj_max[℃]}, MLCC{board flex 한계[mm 또는 µε], termination}, 접점{free_height·working_height 범위[mm], 하중–변위 곡선[N@mm], 도금}, 액추에이터{f0[Hz], Q, 질량[g], 자석 등급}, 스위치 스트로크[mm].
- 지금 — 없음. predict_sed 가 pkg_type·ball_size 를 사람 입력으로 받는다. ODB 의 .package_type 은 굵은 부류뿐이다.
- 빠진 것 — [기타] ODB++ 에는 PCB 랜드만 있고 패키지 볼·두께·PoP 구성이 없다. 사양 표·도구·IR 칸이 어디에도 없다. 접점 응력 여유를 해석으로 요구한 행은 사양서 곡선으로 판단하는 것이 맞아 여기로 합쳤다. 좌석별 핵심 부품 구성(모델·세대)도 이 표에 싣는다.
- 풀리는 도메인(8) — soc · mem · pcb · rel · passive · rf · sh · pwr
- 메커니즘 — thermal.solder_fatigue · new:process.package_warpage · new:mechanical.mlcc_flex_crack · new:interface.contact_spring_stroke · mechanical.vibration
- 질문 예 — DRAM 이 AP 위 PoP 인가 별도 실장·uMCP 인가 / AP 패키지의 볼 피치·볼 지름·바디 두께는 얼마인가 / C-clip 의 작동 높이 범위와 접촉력은 얼마인가
- 선행 — OTH-06
- 근거 — GW search_tools('부품 데이터시트 사양 패키지 볼 지름…') 사양 조회 도구 없음 · GW predict_sed 스키마 · HWAXPortal/docs/procedures/fixtures/odb-hub/sed-mapping.md(행 검증 승계)

#### OTH-09 · 실장 공정 사양(언더필·코너본드·솔더 합금·표면처리·보강판)

**없음 · P0** · 내야 하는 쪽 other(공정·BOM 자료)

- 돌려줘야 하는 것 — {board_id, refdes, 보강 유형(CUF|edgebond|cornerbond|none), 재료명, 필렛 규격[mm], keep-out[mm]}, 보드{solder_alloy, surface_finish(ENIG|OSP)}, 보강판{위치·재질}.
- 지금 — ODB 규칙 CKL-03-002 가 내부 패드 없는 BGA 에 '수지 충전 필요' 를 표시한다. 보강판 위치는 ODB 데이터에 있다(stiffener 층·SUS 부품). 언더필·솔더 재료의 물성은 물성 DB 에 있다.
- 빠진 것 — [기타] 어느 refdes 에 무엇을 적용했는지, 합금·표면처리가 무엇인지는 CAD 밖 자료라 사람이 넣어야 한다. ODB 에 요구할 기능이 아니다. [MCAD] 역할 온톨로지에 언더필이 없다.
- 풀리는 도메인(5) — soc · mem · pcb · material · rel
- 메커니즘 — new:process.underfill_coverage · thermal.solder_fatigue · process.solder · material.corrosion
- 질문 예 — AP·UFS·DRAM 에 언더필·코너본드가 적용되는가 / 솔더 합금과 보드 표면처리는 무엇이고 리비전에서 바뀌었는가
- 선행 — OTH-06 · CROSS-01
- 근거 — ODB/src·api grep(underfill) 0건 · SF/core/data/part_ontology.yaml(roles 16종) · ODB/src/checklist/rules/ckl_03_002.py:1-22(행 검증 승계)

#### OTH-10 · 체결 사양(나사 호칭·토크·예압·순서)

**부분 · P1** · 내야 하는 쪽 other(mcad 메타)

- 돌려줘야 하는 것 — 체결 파트마다 {thread_spec, torque[N·m], preload[N], sequence_no}.
- 지금 — StepForge set_part_metadata 의 meta·note 와 사이드카 extras 에 사람이 적을 수 있고 좌석이 describe_part 로 읽는다.
- 빠진 것 — [MCAD] 약속된 키·단위·검증이 없다. 형상의 screw_diameter 는 모델 원통 지름이지 호칭경이 아니다. [심사 어댑터] 수집하지 않는다. 택소노미상 process.screw_torque 는 시험 전용이고 기본 도구가 없다.
- 풀리는 도메인(2) — mech · rel
- 메커니즘 — process.screw_torque
- 질문 예 — 보스 크랙·풀림 후보 자리의 체결 토크와 예압은 얼마인가
- 선행 — OTH-06
- 근거 — GW search_tools 결과의 set_part_metadata 설명('토크가 얼마인지')·meta 인자 · HR/assets/taxonomy.v1.json(process.screw_torque test-only·[]) · SF/docs/SIDECAR_SPEC.md:90

#### OTH-11 · 넷·레일 전기 조건(최대 전류·공칭 전압·허용 온도 상승·충전 프로파일)

**없음 · P0** · 내야 하는 쪽 other(회로도·전원 트리)

- 돌려줘야 하는 것 — {board_id, net_name, I_max[A], V_nom[V], 리플, ΔT 허용[K], 단계별 충전 전류[A]}.
- 지금 — 값은 어디에도 없다. ODB++ 넷 속성은 샘플에서 비어 있고 계약의 net_class 는 null 허용이다. 담을 일반 통로는 OTH-06 이다.
- 빠진 것 — [기타] 회로도·전원 트리에서 와야 한다. ECAD 넷 노드가 IR 에 없어 넷에 매달 수도 없다. 배선 폭과 동박 두께가 있어도 전류가 없으면 전류밀도·IR drop 이 나오지 않는다.
- 풀리는 도메인(3) — pwr · passive · soc
- 메커니즘 — electrical.si_pi · new:thermal.charging_heat · new:electrical.dc_bias_derating
- 질문 예 — 충전 대전류 경로의 넷별 최대 전류는 얼마인가 / MLCC 가 물린 전원 넷의 전압은 얼마인가
- 선행 — OTH-06 · NF-02
- 근거 — HWAXRisk/docs/odb-adapter-contract.md(net_class|null) · HR/ir_builder.py:574,665 · ODB 샘플 캐시 eda_data.json 넷 속성 0(행 검증 승계)

#### OTH-12 · 안테나 ↔ 대역·기능 매핑과 가해 주파수(클럭·스위칭·고조파) 원장

**부분 · P0** · 내야 하는 쪽 other(RF 사양)

- 돌려줘야 하는 것 — antennas[]{part, feed_refdes, bands[], function(main|div|MIMO|GNSS|WiFi|UWB|NFC|mmW), tx, 최대 전력[dBm]}, aggressors[]{source(refdes|인터페이스), f0[MHz], 확산 여부, 고조파 n·f0[MHz], 겹치는 대역·안테나}.
- 지금 — StepForge set_part_metadata 의 tags·meta·role 에 사람이 적을 수 있고 좌석이 find_parts(tag=)·describe_part 로 읽는다.
- 빠진 것 — [기타] 대역·전력·클럭 주파수는 CAD 에 없어 사람 입력이 유일한 원천이다. [심사 앱] 구조화된 칸과 어휘가 없고 어댑터가 tags·meta 를 읽지 않는다. 가해 주파수 표가 없으면 좌석은 '가깝다' 까지만 말한다.
- 풀리는 도메인(6) — rf · soc · pwr · disp · cam · std
- 메커니즘 — new:electrical.antenna_isolation · new:electrical.desense · electrical.emi · new:electrical.sar
- 질문 예 — 어느 안테나가 어느 대역인가 / 어떤 발진원의 기본파·고조파가 어느 수신 대역에 떨어지는가
- 선행 — OTH-06
- 근거 — GW search_tools 결과의 find_parts(tag)·set_part_metadata 설명 · HR/adapters/mcad.py grep(tags|meta) 0건 · PLAN grep(고조파|주파수 계획) 0건 · HR/risk_store.py:47-61

#### OTH-13 · BOM·공급처·공정 변경(PCN) 입력 채널

**없음 · P0** · 내야 하는 쪽 other(BOM·구매)

- 돌려줘야 하는 것 — {part_number, supplier, grade, effectivity, 변경 종류, 통보 일자, bom.supplier_changed 이벤트}.
- 지금 — 심사 앱에는 없다. 재료가 될 원천 — MCAD 품번, ODB 부품 BOM 속성(벤더·MPN, 원천에 있을 때), 아카이브 온톨로지의 bom·supplier 타입과 supplied_by 관계, StepForge bom_export.
- 빠진 것 — [심사 앱] 소스 종류에 bom 이 없다. 같은 규격·다른 공급처는 diff 0 이라 어느 좌석도 보지 못한다. PCN 원장은 어디에도 없다. 계획이 미결로 적어 둔 항목이다.
- 풀리는 도메인(4) — xd · std · material · rel
- 메커니즘 — material.supplier_change · new:process.bom_change
- 질문 예 — 형상은 같은데 품번·공급처·재질 등급이 바뀐 파트는 무엇인가
- 선행 — OTH-06 · CROSS-02
- 근거 — HR/ir_builder.py:45 · GW list_object_types(bom·supplier·supplied_by — 직접 확인, 변경·PCN 타입 없음) · GW search_tools('BOM 공급처 변경 설계 변경 ECO PCN…') bom_export 뿐 · PLAN:4865(§10 C-43)

#### OTH-14 · 설계 변경 선언 원장(ECO)과 미선언 변경 대조

**없음 · P1** · 내야 하는 쪽 other(설계 관리)

- 돌려줘야 하는 것 — {eco_id, design_rev, 대상(part key|refdes|dim name), 변경 종류, 사유, 기대 값, matched_event_ids[], undeclared_events[], declared_not_found[]}.
- 지금 — 없음. 사이드카는 개정 이력을 note·extras 로 흘려 적을 수만 있다.
- 빠진 것 — [심사 앱] 스냅샷에 설계 리비전 식별이 없고 선언과 diff 이벤트를 대조하는 자리가 없다. 의도 원장이 없으면 좌석은 수백 건의 diff 를 같은 무게로 읽는다. 공급사 통지(OTH-13)와는 다른 것이다.
- 풀리는 도메인(4) — xd · std · mech · pcb
- 메커니즘 — interface.clearance_close · material.supplier_change
- 질문 예 — 검출된 변화 가운데 설계자가 의도했다고 선언하지 않은 것은 무엇인가
- 선행 — NF-04
- 근거 — PLAN:4861(§10 B-39 design_rev 부재) · SF/docs/SIDECAR_SPEC.md:238 · GW search_tools(ECO) 해당 도구 없음

#### OTH-15 · 규격 원문·한계 곡선·문헌 조회 통로

**부분 · P0** · 내야 하는 쪽 other

- 돌려줘야 하는 것 — {규격 번호, 조항, 조건값, 한계값·곡선(예: 변형률 속도 대 허용 변형률), 출처}.
- 지금 — 좌석 유지 목록에 search_scholar·search_web·check_design_rules·get_reference_cases·search_reports 가 있다.
- 빠진 것 — [기타] 웹 리서치와 laminate 백엔드가 오늘 backend_down 이라 그중 넷은 부를 수 없다. 허용 스트레인 한계 곡선을 담는 자리가 없다. 규격을 요구로 등록하는 길은 OTH-03 이다.
- 풀리는 도메인(3) — std · rel · sim
- 메커니즘 — new:mechanical.board_strain · mechanical.drop_stress
- 질문 예 — 이 시험 조건의 규격 원문과 허용 한계는 무엇인가
- 선행 — OTH-03
- 근거 — GW list_tool_apps(heax-web_research_mcp·heax-laminate_analyzer_mcp backend_down·tool_count 0) · AS:662-666

#### OTH-16 · 선례·필드 불량·VOC 이력과 과제를 넘는 부품 정규 키

**부분 · P0** · 내야 하는 쪽 other

- 돌려줘야 하는 것 — {product_code, issue_key, 건수, 기간, incident 객체 id·영향도·조치 상태, 기구 코드 매핑}, 선례{ckey, target_key, cluster_key, mechanism, verdict, 시점}.
- 지금 — get_top_issues·query_voc·search_voc·get_voc_summary·search_objects·get_object·get_subgraph(좌석 유지), 브리프 E10(제품 코드로 미리 조회)·E5(등록부 선례), sameas.compute_ckey, risk_get_precedents·risk_similar_projects.
- 빠진 것 — [사람] 과제 4건 모두 제품 코드가 비어 E10 이 '제품 연결 미등록' 한 줄로 끝난다. [심사 앱] 일이 둘로 나뉜다 — ① voc_map(0행)·failure_map(5행) 사상표를 채우는 일, ② 그 표를 읽는 코드를 만드는 일(지금은 소비처가 없어 채워도 inc:·voc: 가 기구에 자동으로 붙지 않는다). 등록부 0행, 정규 키 5건 전부 candidate·재질 축 na. 러너의 앱 범위가 step_forge·kooremapper 라 risk_ 도구는 좌석에 안 열린다. 브리프가 window_days 를 넘기는데 게이트웨이 인자는 period_days 다(영향 unverified).
- 풀리는 도메인(6) — rel · xd · disp · cam · rf · std
- 메커니즘 — material.adhesive_aging · mechanical.drop_stress · material.supplier_change · new:process.precedent_reuse
- 질문 예 — 필드 이슈가 이번 변경 부위와 겹치는가 / 같은 부품이 다른 과제·이전 리비전에서 어떤 리스크 선례를 가졌나
- 선행 — CROSS-02 · SIM-18
- 근거 — DB rr_projects product_code·product_refs·전작 코드 null 4/4·rr_registry 0·rr_part_keys 5행 candidate·na · HR/brief.py:729-756,837,847-848 · GW get_top_issues 스키마(period_days) · HR grep(voc_map|failure_map) 코드 소비처 0건 · HR/runner.py:191-199 · GW risk_taxonomy 자산(voc_map 0·failure_map 5)

#### OTH-17 · 금형 DFM·사출 해석 결과의 파트 귀속 입력

**없음 · P2** · 내야 하는 쪽 other(금형사 산출물)

- 돌려줘야 하는 것 — {part, weld_line 위치 xyz[mm], gate 위치, 싱크 예상 위치, 변형량[mm], 겹치는 형상(보스·리가먼트·안테나 분절부)까지 거리[mm]}.
- 지금 — 없음.
- 빠진 것 — [기타] 웰드라인·게이트·싱크는 CAD 질의가 아니라 금형사 산출물로 판단한다. 입력 채널이 없다.
- 풀리는 도메인(3) — mech · xd · rf
- 메커니즘 — process.tolerance · mechanical.drop_stress
- 질문 예 — 웰드라인·게이트가 얇은 살·보스·안테나 분절부와 겹치는가
- 선행 — OTH-06
- 근거 — GW search_tools('사출 해석 웰드라인…') 해당 도구 없음 · PLAN grep(moldflow|웰드라인) 0건

### F 비기능 계약

#### NF-01 · 좌석 자유조회 통로·조회 예산·도메인별 계약 문구

**부분 · P0** · 내야 하는 쪽 other(심의 엔진)

- 돌려줘야 하는 것 — 좌석에 열린 도구 이름 집합, 좌석당 조회 예산, 도메인별 필수·권장 도구와 산출 형식.
- 지금 — 접두사 허용목록 + 읽기 목록(step_forge 6·kooremapper 14) + 유지 목록 15 + 물성 도구 18 상시. StepForge 141종 중 32종이 열려 있다(앞 단계 집계).
- 빠진 것 — [심의 엔진] axis_gap·clearance_field·measure_distance·nearest_parts·thickness_report·fastener_report·stackup_profile·section_*·drop_check·identify_part·part_location 등이 접두사에 안 걸려 닫혀 있고 report_query·report_angle_stats·mesh_stack_diagram·sed_sample_from_odb 도 닫혀 있다. 예산이 좌석당 3회다. disp·cam·sh 계약 문구가 같아 도메인 고유 사실을 요구하지 않는다. MCP 워크플로 경로는 좌석 도구 호출이 없다. 스냅샷 수집이 늦어져도 통로만 열면 좌석이 수치를 낼 수 있다.
- 풀리는 도메인(15) — xd · sim · cam · rel · soc · disp · mech · pcb · rf · passive · pwr · sh · mem · std · material
- 메커니즘 — interface.clearance · material.property_uncertain · mechanical.drop_stress
- 질문 예 — 좌석이 형상 수치를 스스로 조회하고 도메인 고유 사실을 요구받는 통로가 있는가
- 선행 — NF-04
- 근거 — AS:644-655,662-666,2061-2105,3110-3139 · HR/planner.py:23-24 · HR/runner.py:191-199 · AS:630-635(disp·cam·sh 계약 문구 동일) · HWAXPortal/infra/pipeline/hwax-risk-review.js:11-12(행 검증 승계)

#### NF-02 · ECAD 어댑터 계약 정합과 심사 diff 의 ecad 이벤트

**계약에만 · P0** · 내야 하는 쪽 ecad + 심사 앱

- 돌려줘야 하는 것 — 계약 4도구에 맞는 응답(또는 실제 도구명에 맞춘 개정 계약), component·net·layer 노드, 이벤트 ecad.component_moved{ΔX·ΔY[mm], ΔRot[deg]}·net_changed·stackup_changed·height_changed.
- 지금 — 계약 문서와 스텁. dev 게이트웨이에 ECAD 앱이 없다. cae00 odb-hub 27도구는 문서 근거다(unverified).
- 빠진 것 — [ECAD + 심사 앱] 계약 4도구 이름이 문서상 실제 도구명과 하나도 맞지 않아 계약부터 고쳐야 한다. ecad 노드와 변경 항목이 0건이라 [c:]·[p:] 인용이 불가능하다. diff 에 ecad 를 다루는 코드가 없다. ECAD 의존 6도메인은 대표 1석 외 보류다.
- 풀리는 도메인(7) — pcb · pwr · rf · soc · passive · mem · xd
- 메커니즘 — electrical.net · interface.cross_file_untrusted
- 질문 예 — base→target 에서 이동·추가·삭제·교체된 부품은 무엇인가(ΔX·ΔY·ΔRot)
- 선행 — CROSS-07 · ECAD 카탈로그 전체
- 근거 — HR/adapters/ecad_stub.py:13,29-41 · HR/diff.py grep(ecad) 0건 · HR/planner.py:143-145 · GW list_tool_apps(18앱에 ECAD 앱 없음) · HWAXRisk/docs/odb-adapter-contract.md · REF §2

#### NF-03 · 단위·척도·각도 부호 규약의 선언과 정합

**부분 · P1** · 내야 하는 쪽 join(전 소스)

- 돌려줘야 하는 것 — 소스마다 {unit_system, 좌표 단위(mm), 두께 단위(mm|µm), 회전 부호 규약(CW|CCW)·면 미러 처리, K파일 단위계}, 소스 간 대각비·두께비.
- 지금 — 게이트 G6 가 mcad 단위 경고·unit_system, dyna/mcad 대각비(0.95~1.05), ecad 단위 변환 실패를 본다. 좌석은 inspect_report·get_project_meta·describe_assembly 로 MCAD 단위를 읽을 수 있다.
- 빠진 것 — [해석] K파일에 단위 선언이 없고 dyna 캡처 0건이라 대각비가 계산된 적이 없다. [ECAD] 좌표는 항상 mm 인데 계약은 mm|mil 선언을 요구하고, 캐시의 회전은 원본 부호를 뒤집어 저장하며 층 두께는 µm 다 — 계약에 부호·단위 규약이 없다.
- 풀리는 도메인(3) — sim · pcb · xd
- 메커니즘 — interface.cross_file_untrusted
- 질문 예 — 해석 모델 단위·척도가 CAD 와 맞는가
- 선행 — NF-02
- 근거 — HR/state.py:255-282 · ODB/src/services/data_service.py:405-412(회전 부호 반전 — 직접 확인) · REF:113 · HWAXRisk/docs/odb-adapter-contract.md(units 선언)

#### NF-04 · 소스 세대 토큰과 좌석 라이브 조회의 스냅샷 고정

**없음 · P0** · 내야 하는 쪽 mcad + ecad + sim + 심사 앱

- 돌려줘야 하는 것 — 스냅샷 sources[].generation(mcad: 형상 키+잣대 키+빌드, ecad: job_id+result_id+source_sha256, dyna: 파일 sha256), 모든 도구 응답의 같은 토큰, evidence_stale(bool)과 강등 사유.
- 지금 — 좌석 호출 원문은 rr_panel_calls 에 보관된다. 스냅샷은 불변이다.
- 빠진 것 — [MCAD·ECAD·해석] 소스는 가변이다 — StepForge 과제는 사람이 고치고 다시 검출하며 ODB 결과는 최신 1건으로 덮인다. 응답이 세대 토큰을 실어야 한다. [심사 앱] 스냅샷 세대와 좌석 호출을 대조하는 규칙이 없다(코드 0건). 라이브 조회에 기대는 모든 have_not_ingested 능력과 변환 원장(CROSS-10)의 결속이 여기에 달려 P0 로 두었다.
- 풀리는 도메인(15) — xd · sim · cam · rel · soc · disp · mech · pcb · rf · passive · pwr · sh · mem · std · material
- 메커니즘 — interface.cross_file_untrusted
- 질문 예 — 좌석이 심의 중에 부른 도구의 값이 스냅샷이 얼린 그 설계의 값인가
- 근거 — HR grep(evidence_stale|geo_key|generation 대조) 0건 · HR/risk_store.py:297(rr_panel_calls) · REF §2(run_* 결과 덮어쓰기)

#### NF-05 · 게이트웨이 응답 캐시의 우회 인자와 신선도 표식

**없음 · P1** · 내야 하는 쪽 other(게이트웨이)

- 돌려줘야 하는 것 — 요청 no_cache(bool), 응답 cache{hit, age_s}, rr_snapshot_calls.cache_hit.
- 지금 — 게이트웨이가 list_·get_·describe_·compare_·report_·inspect_·part_·project_tree 접두 도구를 (백엔드·도구·인자·호출자·소속) 키로 300초 캐시한다. 적중은 게이트웨이 감사에만 남는다.
- 빠진 것 — [게이트웨이] 우회 인자가 없고 스냅샷 원장에 적중 칸이 없다. 같은 백엔드로 비캐시 도구가 지나가야 비워지므로 웹 화면이나 잡 완료로 바뀐 소스는 무효화 계기가 아니다. 제안은 P0 였으나 창이 300초이고 캡처 경로는 비캐시 도구(system_status·interface_graph)가 같은 백엔드를 지나며 비우는 구조라 P1 로 내렸다(호출 순서 보장은 unverified).
- 풀리는 도메인(4) — xd · sim · mech · pcb
- 메커니즘 — interface.cross_file_untrusted
- 질문 예 — 방금 받은 도구 응답은 지금 소스의 값인가, 5분 전 값인가
- 선행 — NF-04
- 근거 — GWS:234-256,276-291,2689-2703 · GWS grep(no_cache) 0건 · DB rr_snapshot_calls 열 목록(cache 칸 없음)

#### NF-06 · 응답 계약 — 페이지·절단 표시, '모름' 과 '없음' 의 구분, 오류 봉투, 인자 이름

**부분 · P1** · 내야 하는 쪽 mcad + ecad + sim

- 돌려줘야 하는 것 — 목록 응답의 {total, returned, has_more 또는 next_offset, truncated}, null 사유(미측정|미실행|해당 없음), 오류는 isError 또는 명시 코드, 계약에 적힌 인자 이름.
- 지금 — 심사 어댑터가 절단·계약 결손을 degraded·contract_missing 으로 남긴다. DynaForge 설명이 '빈 배열은 부재가 아니다' 를 명시한다.
- 빠진 것 — [ECAD] 문서상 페이지는 page·page_size·has_more 인데 계약은 offset·limit·next_offset 이다. 체크리스트 미실행의 빈 배열이 '위반 없음' 과 똑같이 생겼고 오류가 HTTP 200 + error 키다. 핀은 200개에서 잘린다. [MCAD] part_mesh_map 기본 limit 100 을 어댑터가 넘기지 않는다. [해석] 어댑터가 limit 로 부르는 도구의 인자가 top_n 이다. min_safety_factor null 은 안전이 아니다.
- 풀리는 도메인(4) — pcb · sim · xd · soc
- 메커니즘 — interface.cross_file_untrusted
- 질문 예 — 빈 응답이 '없다' 인가 '아직 안 돌렸다' 인가
- 선행 — NF-02
- 근거 — REF:8-33(대조 #8·#10)·REF:123 · HWAXRisk/docs/odb-adapter-contract.md(offset·limit) · SF/app/mcp_server.py:2298 · HR/adapters/dyna.py:230 대 GW report_worst_cases 스키마 · GW list_tool_apps(heaxkooremapper_mcp_list_reports 설명)

#### NF-07 · 택소노미 메커니즘 등재와 가족 확장

**없음 · P1** · 내야 하는 쪽 other(심사 앱)

- 돌려줘야 하는 것 — 코드마다 {code, mechanism(가족), detail, label, default_detectability, default_tools, 동의어}. 가족 후보 acoustic·optical·sensor·contamination.
- 지금 — mechanism 38종·가족 6종. 없는 코드는 '<가족 또는 process>.unclassified' 로 접히고 원문은 mechanism_free 에 남는다.
- 빠진 것 — [심사 앱] cluster_key 가 (mechanism, detail, subject_key, change_kind)라 같은 파트·같은 변화의 다른 물리(안테나 디튠과 SAR, 보드 스트레인과 MLCC 크랙)가 한 클러스터로 뭉친다. 이 목록 입력 행에서만 new: 코드가 32종이고 가족 밖이 7종이다. 근거 수집은 막지 않으므로 P1 로 두되 board_strain·antenna_detune 처럼 도메인 핵심 기구를 먼저 올린다.
- 풀리는 도메인(8) — sh · cam · rf · pwr · pcb · passive · disp · mech
- 메커니즘 — new:mechanical.board_strain · new:electrical.antenna_detune · new:electrical.sar · new:mechanical.mlcc_flex_crack
- 질문 예 — 새로 쓴 메커니즘 코드가 등록부에서 서로 구분되는가
- 근거 — HR/assets/taxonomy.v1.json(mechanism 38·가족 6 — 직접 집계) · HR/narrative.py:921-925,938-957

#### NF-08 · 엔진 소비처 확장 — 새 사실을 읽는 신호·규칙·성격 씨앗·특징 차원·diff 속성

**없음 · P1** · 내야 하는 쪽 other(심사 앱)

- 돌려줘야 하는 것 — 신호(스택업 총두께·층수·비대칭, 부품 높이 상위, 체크리스트 위반 수, 부품 상면 최소 간극), 특징 차원(n_layers·board_thickness_mm·n_bga·n_fasteners·n_joints), diff 속성·이벤트(부품 높이·층 두께·체결·조인트·교차 간극).
- 지금 — ECAD 신호는 개수 2종, 특징 22차원 중 ECAD 는 n_ecad_cmp 하나, 규칙 7종은 전부 mcad·dyna·req 입력, 성격 씨앗 규칙 16종, diff 노드 속성은 닫힌 목록이다.
- 빠진 것 — [심사 앱] 사실이 스냅샷에 실려도 읽는 자리가 없으면 브리프·유사 과제 검색·선례·diff 이벤트가 보드·체결·적층 차이를 보지 못한다.
- 풀리는 도메인(8) — pcb · soc · mem · rf · passive · pwr · mech · xd
- 메커니즘 — process.warpage · interface.clearance_close
- 질문 예 — 새로 들어온 사실을 신호·규칙·유사 과제 벡터가 실제로 읽는가
- 선행 — NF-02 · CROSS-33 · SIM-20
- 근거 — HR/state.py:33-38,366-372 · HR/assets/rules-seed.v1.json(7종)·character-seed-rules.v1.json(16종) · HR/diff.py:947-957

#### NF-09 · 좌석 적용성 사실표 — 좌석별 필요 사실과 스냅샷 보유 사실의 대조

**없음 · P1** · 내야 하는 쪽 other(심사 앱)

- 돌려줘야 하는 것 — {좌석 키, 필요 사실 태그, 보유 사실(소스·역할·ecad 속성·사실 원장 kind), 판정(착석|보류 reason=no_design_fact)}.
- 지금 — 보류는 도메인 단위 ecad_absent 하나뿐이다.
- 빠진 것 — [심사 앱] 형상·보드 사실로는 평가할 것이 없는 좌석이 많다. mem 16석을 직접 보니 패키징·휨·열·전력 넷을 뺀 12석(리텐션·ECC·LDPC·로우해머·UFS 프로토콜·FTL 등)은 ECAD·MCAD 어느 능력으로도 볼 사실이 없다. 이 좌석들은 능력을 다 갖춰도 일반론만 낸다. 다른 도메인의 비율은 이번에 세지 않았다(unverified).
- 풀리는 도메인(6) — soc · mem · cam · disp · sh · xd
- 질문 예 — 이 좌석이 평가할 사실이 스냅샷에 하나라도 있는가
- 선행 — OTH-06 · OTH-08
- 근거 — GW list_agents(domain='mem', 16석 목록) · GW list_agent_domains(xd 122·sim 22·cam 21·rel 20·soc 20 등) · HR/planner.py:143-145 · HR/assets/taxonomy.v1.json(domain.ecad_dependent 불리언)

#### NF-10 · 검증용 정렬 실물 3소스 세트와 결속 원장(같은 제품·같은 시점, 리비전 2판 이상)

**없음 · P0** · 내야 하는 쪽 other(사람 + 전 소스)

- 돌려줘야 하는 것 — {product_code, milestone(dev_rev), stepforge project_id, 보드별 odb job_id, dyna session_id·file_id·report_ids, detect_job_id, 캡처 일시, 소스별 원본 해시} 두 판 이상.
- 지금 — 심사 스냅샷 4건은 전부 3파트짜리 픽스처 과제 하나다. 해석 리포트 0건, 아카이브 해석 런 0건, dev 게이트웨이에 ECAD 앱 없음.
- 빠진 것 — [사람] 이 세트가 없으면 나머지가 모두 구현돼도 same-as·좌표 정합·결과 오버레이·리비전 diff 를 실데이터로 한 번도 검증할 수 없고 좌석 인용 분포도 잴 수 없다. ECAD 를 낀 검증은 cae00 에서만 가능하다.
- 풀리는 도메인(15) — xd · sim · cam · rel · soc · disp · mech · pcb · rf · passive · pwr · sh · mem · std · material
- 메커니즘 — interface.cross_file_untrusted · mechanical.drop_stress
- 질문 예 — 같은 제품·같은 시점의 기구·보드·해석이 한 스냅샷에 묶여 있고 견줄 리비전이 두 판 이상 있는가
- 선행 — CROSS-04 · CROSS-07
- 근거 — DB rr_snapshots 4건 kinds [mcad, ecad]·ecad_absent·REST 경로가 한 과제 · GW report_corpus(reports 0) · GW list_analysis_runs(total 0) · GW list_tool_apps · HWAXRisk/checklist.md:274(앞 단계 조사 승계)

### 넣지 않은 것 — 14건

- disp-cam-24·soc-mem-34·soc-mem-64 의 상태 have(낙하 파트 위험표) — 코드 경로는 있으나 실캡처가 0건이고 브리지 0건·sim_params 미적재·인자 불일치가 겹쳐 실데이터로 돈 적이 없다. SIM-01 에서 partial 로 정했다(도전 둘을 받아들였다).
- disp-cam-11 의 상태 have_not_ingested(적층 중립축) — Laminate Analyzer 는 오늘 backend_down 이고 남은 도구 mesh_stack_diagram 은 좌석에 닫혀 있으며 층별 변형률을 내지 않는다. SIM-14 에서 partial 로 맞췄다.
- pcb-passive-31 의 상태 missing(보드 변형률) — 파트 단위 변형률·주응력·시계열은 게이트웨이에 있다. 없는 것은 위치 단위와 속도 칸이라 SIM-03 에서 partial 로 합쳤다.
- pwr-23·mech-xd-18 의 상태 partial(소비전력) — 값은 어디에도 없다. partial 의 근거였던 일반 통로(const: 선언 치수)는 OTH-06 으로 분리하고 OTH-07 은 missing 으로 두었다.
- rf-11 을 별도 해석 능력으로 두는 것(접점 스프링 응력 여유) — cclip op 은 하중–변위를 입력으로 받는 덱 전처리이고 현업은 사양서 곡선으로 판단한다. OTH-08 과 CROSS-28 로 흡수했다(도전 수용).
- rf-21 도전의 상태 표기 missing(인스턴스 refdes) — 인스턴스 유일성이 소스 단계에서 없다는 지적은 받아들여 CROSS-02 에 적었다. 다만 품번 수준 키와 designator 칸은 게이트웨이 도구가 이미 내므로 상태는 partial 이다.
- soc-mem-11 도전의 '스크류 보스는 보드 고정홀과 같은 자리이므로 join 이 아니다' — 보드 고정홀 기준 1차 값은 ECAD 단독으로 내야 한다는 점은 받아들여 CROSS-22 에 적었다. 그러나 구멍 없는 지지(쉴드캔 벽·브래킷·리브)와 MCAD 스팬은 변환이 있어야 하고 홀↔보스 대응 자체가 확인되지 않았으므로 join 항목은 남긴다.
- soc-mem-32 도전의 '열·전자기 결과 행을 시험 결과 통로 한 행으로 합치기' — 패키지 휨 자료의 side 는 other 로 옮겼고(SIM-10) 열 5행·전자기 1행은 각각 하나로 합쳐 '해석 또는 측정' 으로 적었다. 그러나 돌려줄 칸(℃ 대 dB·W/kg)과 공급 주체가 달라 SIM-11·SIM-12·SIM-18 셋으로 나눠 두었다.
- 제안 '판 일치 검문' 을 P0 단독 행으로 두는 것 — 외곽·고정홀 잔차는 CROSS-10 의 산출로 넣었다. refdes 단위 잔차표는 부품 바디가 실린 과제와 인스턴스 refdes 가 있어야 하므로 CROSS-11 로 두되 P1 이다.
- 제안 '계면 쌍 동적 간극 닫힘' 의 상태 missing — report_energy_flow 가 케이스별 접촉 엣지의 peak_force·total_work 를 이미 주고 좌석에 열려 있다. 없는 것은 최소 동적 간극과 상대 변위라 SIM-07 에서 partial 이다.
- 제안 '게이트웨이 캐시 우회' 의 우선순위 P0 — 창이 300초이고 캡처 경로는 비캐시 도구가 같은 백엔드를 지나며 비우는 구조다. 세대 토큰(NF-04)이 본질이라 NF-05 는 P1 로 두었다.
- 제안 '택소노미 메커니즘 등재' 의 우선순위 P0 — 미등재 코드는 근거 수집을 막지 않고 원문이 mechanism_free 에 남는다. 등록부 병합 문제라 NF-07 은 P1 로 두었다.
- 제안 '좌석 적용성 사실표' 의 '핵심 부품 구성표' 를 별도 능력으로 두는 것 — 부품 모델·세대·인터페이스 규격은 품번 사양 표와 같은 입력이라 OTH-08 에 포함했다.
- sim-rel-std-01 도전(sim·rel·std 81행의 메커니즘 칸 공백)을 행 단위로 고치는 것 — 입력 행 자체는 이 단계에서 고칠 수 없다. 대신 그 행들이 들어간 항목마다 unlocks_mechanisms 를 택소노미 코드로 채웠고 std 가 맡을 creepage·emi 는 CROSS-29·CROSS-27·OTH-12 가 받도록 적었다.

## 도메인별 최소 세트

이것이 없으면 그 도메인 좌석은 일반론에 머문다(도메인 묶음별 도출 단계의 결론, 괄호 안은 도출 행 번호).

### mech — 기구 구조 / 기구·구조

mech 19석의 페르소나는 갭 분포·보스/스크류 배치·살두께·접착폭·압착·낙하 하중 경로를 다루는데 스냅샷이 주는 것은 쌍당 min_gap 과 bbox 뿐이다. 필요한 측정은 대부분 StepForge 게이트웨이에 이미 있고(64행 중 have_not_ingested 21) 수집과 좌석 통로만 막혀 있다.

- 간극·압착의 분포와 축방향 간극(clearance_field · axis_gap · measure_distance)을 스냅샷에 싣고 좌석 통로를 연다 — 검출 범위 0.5 mm 밖 쌍 포함(mech-xd-04·05·17·39)
- 체결·보스·조인트·강체 증명(graph 잡 산출물: fastener_report · fastener_distribution · list_joints · structure_report · rib_boss_features)을 노드·엣지 속성으로 수집한다(mech-xd-07·08·33·36)
- 실제 최소 벽 두께와 단면 성질(thickness_report · section_profile · stiffness_jump)을 수집해 min_dim 근사를 대체한다(mech-xd-10·30)
- 재질명·밀도·역할(사이드카 material, StepForge role)과 검출 잣대(get_project_meta.tol_config)를 어댑터가 읽는다 — diff 의 수치 이벤트와 물성 조회 키가 함께 살아난다(mech-xd-02·16·37)
- 실링·접착 경로의 폐루프 여부와 위치별 폭을 내는 신규 조회, 그리고 결합 수단(접착·스크류·후크)의 구조화 사실(mech-xd-12·16)
- 낙하 근거 두 겹 — drop_check 사전 지표 수집과 report_part_risk 실캡처 + CAD↔PID 브리지 수리(mech-xd-24·25·59)

### xd — XD(외관·조립 설계) — taxonomy.v1.json / 업무·프로세스(교차 도메인) — browse_experts 조직도

xd 122석 중 설계 사실을 보는 좌석(change-impact · gap-check · tolerance-check · bom-impact · mcad-geometry · ecad-read 계열)은 변경 목록·실효 갭·공차 체인·BOM·데이터 정합을 묻는다. 계약이 요구하는 '조립 순서·공차 여유·서비스성'과 [d:] 인용은 원천이 0건이고, 나머지 프로세스·거버넌스 좌석은 CAD 기능이 아니라 로스터 범위 결정으로 풀 사안이다.

- 비교 성립 근거(단위·파일 해시·tol_config·사이드카 적용·사람 수정 건수)와 재파싱된 부피·무게중심으로 리비전 diff 를 수치까지 복구한다(mech-xd-41·43)
- 공차·요구 채널 — 명명 치수에 공칭·공차(±)와 체인 합산을 싣고(StepForge 치수 기록부 수집 포함) rr_requirements 에 한계·필수 시나리오를 등록한다(mech-xd-31·32·49·57)
- ECAD 부품 배치·높이·외곽 다각형·고정홀의 목록형 노출(계약 개정)과 보드→어셈블리 좌표 변환·refdes↔MCAD 사전(mech-xd-20·21·26·46·47·54·56)
- BOM·공급처 입력 채널(소스 종류 bom, 품번·공급처·등급, bom.* 이벤트)(mech-xd-50·51·52)
- 조립 순서·삽입 방향·분해 접근성 데이터와 삽입 경로 간섭 조회(mech-xd-48)
- CAD 파트↔해석 PID 브리지 수리(part_mesh_map 응답 키 parts, mesh_report 로 stale 판정)(mech-xd-59)

### disp — 디스플레이 모듈 / 디스플레이

disp 좌석 19석 가운데 CAD 로 말할 수 있는 좌석(모듈 본딩·폴더블 적층·UTG 커버윈도우·TFE 측면 침투·UPC)은 적층·간극·반경·접착 띠 네 가지 수치로 판단한다. 지금 스냅샷에는 0.5 mm 이하 쌍의 min_gap 과 띠 폭 스칼라만 있고 그 변화마저 공차 잣대 미확인으로 빠지므로, 이 여섯이 없으면 좌석은 '폴더블은 접힘부가 취약하다' 수준의 일반론에 머문다.

- 디스플레이 구성 파트의 층 단위 역할 분류를 스냅샷에 싣기 — 윈도우·UTG·OCA·패널·쿠션·서포트 플레이트·힌지(disp-cam-02, 55)
- 적층 프로파일 수집 — stackup_profile 의 층 순서·층별 두께·층간 간극·재질명을 rr_ir 에 실어 diff 와 인용 단위로 만들기(disp-cam-06, 08)
- 간극의 분포와 리비전 변화 — tol_config_hash 복구로 iface.gap_changed 를 살리고, clearance_field·axis_gap 으로 윈도우 에지–립과 패널 배면 간극을 재며, utg_edge_gap 같은 명명 치수를 정의하기(disp-cam-03, 04, 16)
- 접힘 형상 — bend_profile 의 내측 반경·각도와 list_joints 의 힌지 축을 IR 속성이나 명명 치수로 받기(disp-cam-10, 12)
- 접착 띠 폭·밴드 면적의 변화 이벤트와 띠 경로(최소 폭 위치·폐루프)(disp-cam-14, 15)
- 낙하·국부 충격 결과의 실캡처와 판정 기준 등록 — report_part_risk·report_directional, rr_requirements(disp-cam-24, 26, 27)

### cam — 카메라 모듈 / 카메라

cam 좌석 21석 중 다수(렌즈 설계·화질·센서 리드아웃·ISP)는 CAD 사실이 거의 없고 사양이 들어와야만 말할 수 있다. CAD 로 답할 수 있는 좌석(모듈 신뢰성·OIS 제어·VCM·폴디드·시스템 아키텍처)은 돌출·Z 여유·스트로크 간극·자석 거리·고정 방식으로 판단하는데, 계약 문구가 disp·sh 와 같아 이 사실을 요구하지도 않고 스냅샷에도 없다.

- 카메라 구성 파트 분류 — 모듈·데코·윈도우·브래킷과 자석·가동부를 식별해 스냅샷에 싣기(disp-cam-36, 40, 55)
- 모듈 6면 축방향 간극과 범프 돌출·윈도우 매립 명명 치수 — axis_gap·clearance_field 수집과 bbox_world 기반 추출식 정의(disp-cam-38, 29, 53)
- 가동부 스트로크 간극과 모듈 사양 입력 — 축별 간극 대 스트로크·허용 G·모듈 실중량·화각을 요구로 등록(disp-cam-39, 27)
- 자석 대 센서·자성체 거리 — 자석 식별, ECAD 홀 IC·자이로 위치 노출, 보드→어셈블리 좌표 변환(disp-cam-40, 41, 42, 22)
- 낙하 시 모듈 G·윈도우 응력의 실캡처와 첫 접지 파트(disp-cam-50, 28)
- 모듈 고정 방식과 개구 실링 틈 — what_holds·describe_part, leak_report(disp-cam-43, 48)

### sim — 해석(CAE) / 시뮬레이션·해석

앞의 넷이 없으면 sim 좌석은 해석 결과가 이 리비전의 것인지, 조건이 충분한지, 믿을 만한지를 판정할 수 없어 파트별 최악값 인용이 성립하지 않는다. 다섯째가 없으면 판정 기준이 좌석 경험이 된다. 여섯째는 휨·솔더·SED 좌석이 도구를 부를 수 있게 하는 입력이다.

- mcad↔dyna 대응 복구 — part_mesh_map 의 parts 키 읽기와 stale 판정(mesh_report.artifacts.kfile), modelmeta bbox 에서 size 유도 (행 01·02)
- 리포트 ↔ K파일 ↔ STEP 리비전 결속을 스냅샷에 고정 (행 03)
- 결과층에 값 적재 — drop_height·doe_strategy·n_cases·sim_params.yield_stress·에너지 수지, 그리고 실리포트 1건으로 경로 실증 (행 12·14·15·34)
- CAD 재질명과 밀도 원천 — 재질 → 물성 카드 해결 결과와 질량·무게중심 (행 05·33)
- 과제 필수 시나리오를 조건값(높이·방향·횟수)과 함께 등록 (행 13)
- ECAD 스택업·층별 동박률·부품과 핀 좌표, 보드↔모델 좌표 정합 (행 19·20·21·22·24)

### rel — 신뢰성

rel 좌석의 산출 요건은 trigger_condition 명시와 선례 범위 판정이다. 조건(요구)·위치(형상과 ECAD 좌표)·선례(RA·VOC) 세 축이 모두 비어 있어 지금은 시험 일반론만 가능하다. 공차 잣대는 이미 실리는 간극·접착 폭 수치가 리비전 diff 에서 제외되지 않게 하는 가장 싼 조치다.

- 시험 조건과 합격 기준의 요구 원장(조건값 칸 포함) (행 39)
- 낙하·체결·실링 형상 사실의 적재와 좌석 통로 — drop_check 첫 접지, fastener_report·fastener_distribution, leak_report, 구역(zone) (행 40·42·46·55·61)
- 검출 공차 잣대(tol_config_hash) 복구로 간극·접착 폭·간섭량 변화 이벤트 살리기 (행 41·56·60)
- ECAD 부품·핀 좌표, 보드 외곽 다각형·고정홀, 체크리스트 결과 노출과 좌표 정합 (행 44·45·47·48·51)
- 선례·필드 채널 — 과제 product_code 등록과 voc_map, RA incident·test_run 의 조건 구조화, get_reference_cases 복구 (행 66·67)
- 해석 소견을 파트·케이스에 묶고 SED 예측 입력을 채우기 (행 43·54)

### std — 규격·표준 / 표준·규격

std 는 필수 근거가 도구가 아니라 요구 원장인 유일한 도메인이다. 원장이 0행이고 조건값 칸이 없으며 원문 조회 도구가 게이트웨이에 없어, 지금 앉으면 '요구 미등록 — 등록 제안' 만 남는다. ECAD 항목은 패키지 아웃라인·메모리·열계측 좌석 3석이 설계 값을 받는 유일한 길이다.

- 적용 규격을 kind='standard' 요구로 등록 (행 73)
- 조항별 시험 조건값의 구조화와 해석·시험 조건 대조 — scenario_map, 리포트 조건값 적재, 방향 집합 (행 74·75·85)
- 규격 원문 조회 통로와 판 유효성 — search_scholar·search_web·check_design_rules 복구 또는 규격 카드 (행 76)
- 명명 치수와 dim_limit 로 한계 대비 여유 계산, rr_ir 밖 측정값을 치수로 끌어오는 길 (행 90)
- 변경 종류 원장 — 기구 diff 에 ECAD 부품 변경과 공정·공급사 변경(PCN)을 더하기 (행 79·80·81)
- ECAD 풋프린트·핀 수·피치·패드, 스택업·보드 두께 (행 77·78·83·86)

### material — 재료 / 소재

좌석은 한 명이고 MaterialTwin 조회 도구는 이미 열려 있다(06·32번 have). 막힌 곳은 물성 DB 가 아니라 '이 과제의 어느 파트가 어느 재료인가' 다. 관측 표본 전부에서 재질이 null 이라 지금은 비교 대상이 없다. 앞의 셋이 서면 재료 교체 delta 를 수치로 낼 수 있고, 넷째가 서면 이종재료 계면을 위치로 지목할 수 있다.

- 파트별 재질명·밀도가 사람·사이드카 지정분까지 스냅샷 노드에 실리는 통로(REST 채널이 nodes.material 을 읽고 from 을 함께 싣는다) — 01·05번
- 과제 단위 재질 해석표(resolve_materials 의 출처·카드 종류·미해결·의심 공유값)를 스냅샷에 싣거나 좌석 통로에 여는 것 — 02·04번
- CAD 재질명 ↔ MaterialTwin material_id 대응 원장 — 03번
- 계면 쌍 × 재질 조합 표(interface_summary by material 또는 IR 엣지–노드 재질 조인 신호) — 07번
- 해석 재료 카드의 평탄화(E·nu·rho·sigy)와 CAD 파트 ↔ 해석 PID 대응 복구 — 22·23번
- 과제 환경 조건(온도·습도·사이클)과 하중 조건의 정형 등록 — 14·33번

### sh — SH(taxonomy.v1.json, 풀이 없음) / 센서·음향(browse_experts)

sh 는 ECAD 비의존으로 분류돼 전원 착석하지만 센서·마이크 위치는 ECAD 에만 있고 음향 형상량(백볼륨·누설·실 압축)은 좌석이 닿지 못하는 도구에만 있다. 지금 좌석이 받는 것은 모듈 주변 계면 목록(41번) 하나이고 그 모듈이 어느 파트인지도 이름으로 찾아야 한다.

- 음향·햅틱·센서 모듈의 역할과 구역을 스냅샷 노드 속성으로(온톨로지에 LRA·자석·멤브레인·센서 역할 추가) — 42번
- 음향 공동 체적·틈 목록·실 면 밀착 분포(build_cavity·leak_report·clearance_field)를 스냅샷 치수나 좌석 통로로 — 43·44·45번
- ECAD 부품 배치(센서·마이크 refdes·x·y·side·height)와 보드 외곽·협폭부·고정홀 — 48·51·52·65번
- 보드 좌표계 → 어셈블리 좌표계 변환 원장 — 49번
- 0.5 mm 밖 쌍의 3D 거리 질의(measure_distance·nearest_parts)를 좌석 통로로 — 54번

### pcb — PCB / 기판(PCB)

앞의 넷이 없으면 휨·보드 굽힘·접합 신뢰성 좌석이 수치와 refdes 없이 말한다. 다섯째가 없으면 '고정점에서 몇 mm' 같은 기구 결합 질문이 전부 막힌다. 여섯째가 없으면 base→target 심사인데 인용할 변경 항목이 0건이다

- 스택업 층 표와 보드 요약 — 층별 종류·두께[µm]·자재, 총두께[mm], 신호층 수, 표준 스택업 판정 (pcb-passive-01·03)
- 층별 잔동률(POWER_GROUND 포함)과 그 위의 상·하 동박 불균형[%]·스택업 비대칭 지수 (pcb-passive-04·05·06)
- 부품 배치 목록 + 패키지 외형 — refdes·side·x·y·rot(부호 규약)·pkg 폭·길이·pitch·핀 좌표·높이·분류 (pcb-passive-08·21·28)
- 보드 외곽 다각형·컷아웃·고정홀과 협폭부 (pcb-passive-09·13)
- 보드 좌표계→어셈블리 좌표계 변환과 refdes↔MCAD 파트 키, 기구 쪽 고정점·무지지 스팬·역할 식별의 스냅샷 수집 (pcb-passive-10·11·12·23·42)
- 리비전 비교를 심사 diff 로 — 부품 이동·교체와 체크리스트 전이를 ecad.* 이벤트와 인용 id 로 (pcb-passive-36·37·38)

### passive — 수동 소자 / 수동부품

MLCC 크랙·음향·툼스톤·디커플링 좌석은 '어느 소자가 어디에 어느 방향으로' 가 판단의 전부다. 계약 4도구는 rot·footprint 이름만 줘서 사이즈·장축·핀 대응을 낼 수 없고, 변형률과 굽힘 방향은 지금 어느 쪽에도 없다

- 소자 목록 — 분류·사이즈 코드·면·좌표·장축 각도 (pcb-passive-44·45)
- 외곽·컷아웃·고정점까지 거리와 변 대비 방향, 굽힘 주방향 (pcb-passive-46·48·49)
- 배치·이격 규칙 결과의 행 단위 조회(CKL-02 계열·쉴드캔·OSC)와 실제 관리부품 목록 (pcb-passive-50·51·52·66)
- 부품 속성과 핀 단위 넷 — value·정격전압·공차·MPN·벤더·실장 여부, refdes.pin→net·좌표 (pcb-passive-55·59·61)
- 소자 위치의 보드 변형률 또는 그 대용인 지지 스팬·굽힘축 (pcb-passive-53, pcb-passive-12)
- MCAD 칩 바디의 인스턴스 단위 refdes 키 (pcb-passive-70)

### soc — SoC·프로세서 / AP·SoC·패키지

soc 20석 중 CAD 사실로 풀리는 좌석은 패키지·열 계열 8석 안팎(soc-cpi·soc-pop-stackup·soc-warpage·soc-pkg-reliability·soc-thermal-throttling·soc-pdn·soc-substrate·soc-fowlp)이다. 이들의 공통 전제는 'AP 가 어디 있고 어떤 패키지이며 그 위·아래에 무엇이 있는가' 인데 지금은 ECAD 노드 0건, 패키지 사양 0건, AP 바디가 실린 MCAD 판 0건이라 좌석 계약의 권장 도구 predict_sed 조차 인자를 채울 수 없다.

- ecad.components_list + ecad.part_role — AP·CP·PMIC 가 어느 refdes 이고 어느 면·좌표·회전·높이인가(계약 odb_list_components 를 좌표·높이 포함 목록으로 실제 노출하고, ODB 의 ap_memory 분류를 역할 칸으로 내보낸다)
- ecad.package_geometry + other.package_spec — 볼 피치·볼 수·코너 볼 좌표·DNP(ODB 가 이미 파싱)와 패키지 종류·볼 지름·두께·PoP 여부(어디에도 없어 사람·사양 입력 자리가 필요)
- ecad.stackup + ecad.revision_compare — 보드 총두께·층 구성과 리비전 간 부품 이동·품번 변경이 심사 diff 의 ecad.* 변경 항목으로 서야 한다
- mcad.z_gap_axis + mcad.tim_contact — AP 위 Z 간극과 TIM 밀착 분포(게이트웨이 도구는 있으나 스냅샷 미수집·좌석 통로 밖, AP 바디가 실린 MCAD 판 필요)
- join.refdes_sameas + join.board_to_assembly_transform — refdes↔MCAD 파트↔해석 pid 대응과 보드→어셈블리 좌표 변환(없으면 ECAD 사실과 기구·해석 사실이 한 문장에 못 들어간다)
- other.power_map — 부품별 소비전력(열 좌석의 첫 입력, CAD 에서 유도 불가)

### mem — 메모리 / 메모리·스토리지

mem 16석 중 CAD 사실로 풀리는 좌석은 mem-packaging·mem-warpage·mem-thermal·mem-lpddr-phy-si 넷과 부분적으로 mem-ufs-protocol·mem-power 다. 나머지 10석(셀·ECC·FTL·프로토콜·수명 통계)은 어떤 CAD 능력으로도 발언 근거가 생기지 않으므로 ECAD 가 붙어도 deferred 를 푸는 대상에서 빼는 것이 맞다.

- ecad.part_role + ecad.components_list — DRAM·uMCP·UFS 가 어느 refdes·면·좌표인가(ap_memory 범주에 UFS 를 더해 역할 칸으로 노출)
- ecad.package_geometry + other.package_spec — 메모리 패키지 볼 배열·코너 볼·DNP 와 PoP/uMCP 구성·두께(PoP 상부 패키지는 ECAD 배치만으로 알 수 없다)
- other.underfill_plan — 언더필·코너본드 적용 대상·재료·필렛(어디에도 없다)
- ecad.stackup + ecad.copper_balance — 보드 두께·층 구성과 층별·국부 동박률(보드레벨 수명·휨의 입력)
- ecad.revision_compare — 메모리 품번·위치 변경을 변경 항목으로(2nd source 리스크는 형상 diff 에 안 보인다)
- join.refdes_sameas — 메모리 refdes 를 MCAD 간극·해석 결과에 귀속

### pwr — 전원·배터리

pwr 18석은 둘로 갈린다. 팩 · 스웰링 · 안전 계열(pack-integration · swelling · thermal-runaway)은 MCAD 간극 하나와 허용치 하나만 있으면 구체적 소견이 나오는데, 지금은 그 간극이 스냅샷에 없고 좌석이 재는 도구도 못 부른다. 충전 · PMIC · DC-DC 계열(charger-ic · pmic-power-tree · dcdc-regulator · input-protection · protection-circuit)은 부품 · 핀 · 넷과 배선 폭이 있어야 하는데 게이트웨이에 ECAD 도구가 0종이다. 둘을 잇는 질문(발열원↔셀, 서미스터↔셀)은 좌표 변환이 없으면 성립하지 않는다. 이 여섯이 없으면 좌석은 list_parts(name_like) 한 번과 'ecad_absent 명기' 로 끝난다.

- (MCAD) 셀 둘레 방향별 간극의 스냅샷 적재 — 셀을 role=battery 로 집고 axis_gap(z · x · y) · clearance_field 결과를 계면 attrs 또는 명명 치수로 동결해 diff 와 [d:] · [e:] 인용에 싣는다. 0.5 mm 밖 쌍 포함(pwr-01 · 08 · 11)
- (other) 셀 사양 · 스웰링 허용치 · 넷별 최대 전류의 요구 등록 — rr_requirements 에 dim_limit 과 그 짝 치수, 그리고 넷 단위 전기 조건을 담을 칸(pwr-02 · 18)
- (ECAD) 부품 목록의 실노출 — refdes · 좌표 · 면 · 높이 · 속성(VALUE · VOLT · FNC 등)과 핀 단위 넷 · 좌표, 보드 전체 넷 목록. 계약 4도구의 components · nets 에 핀과 속성을 더한 것(pwr-15 · 19 · 21 · 26 · 27 · 39)
- (ECAD) 넷 형상 요약 조회 — 넷 이름을 주면 층별 배선 폭 · 길이 · 최소 폭 · 비아 수 · 면 면적, 그리고 층별 동박 두께. 계약 조건 5 가 뺀 범위(pwr-16 · 17)
- (join) 보드 좌표계→어셈블리 좌표계 변환의 저장과 그 위의 부품↔기구 거리 조회(pwr-22)
- (MCAD) 무선충전 · 열경로 적층의 환원 — stackup_profile 의 층 순서 · 두께 · 간극 적재와 코일 · 차폐 시트 · 그라파이트 역할 추가(pwr-30 · 31 · 33)

### rf — RF·안테나 / 무선(RF)

rf 좌석이 묻는 사실은 절반이 기구 형상(방사체 주변 금속·슬릿·접점 눌림·레이돔), 절반이 보드(접점·노이즈원 위치·넷·동박·차폐 패드)다. 기구 쪽은 게이트웨이 도구가 이미 값을 내지만 스냅샷에 실리지 않고 좌석 통로도 닫혀 있으며, 무엇이 방사체인지와 재질이 비어 있어 대상을 못 잡는다. 보드 쪽은 dev 게이트웨이에 도구가 0종이다. 두 쪽을 한 문장에 넣으려면 좌표 정합이 필요하고, 대역·전력처럼 CAD 에 없는 값은 사람이 등록해야 판정 기준이 생긴다. 이 여섯이 없으면 19석이 디튠·디센스·차폐·SAR 를 경험칙으로만 말한다.

- 방사체·접지 금속 식별 — 파트 역할(antenna·shield_can·connector 등)과 재질 이름을 IR 노드 속성으로 싣고, 이름에 ANT 가 없는 방사체는 사람이 role 을 지정한다 (rf-04, rf-05)
- 방사체 기준 거리의 적재 — nearest_parts·measure_distance·axis_gap·clearance_field 결과를 clearance_gap 0.5 mm 한도 밖까지 IR 엣지와 명명 치수로 싣고, 리비전 diff 를 방사체 반경으로 거른다 (rf-01, rf-03, rf-17, rf-37)
- ECAD 부품 배치·넷 목록 — refdes·좌표·면·높이·기능 역할이 든 부품 목록(ANT·RF 접두 부품 포함)과 보드 전체 넷 목록, 그리고 두 리비전의 부품 차이 (rf-08, rf-19, rf-22, rf-38)
- 보드 영역·차폐 조회 — 지정 영역의 층별 동박·GND 유무와 쉴드캔 접지 패드의 최대 개구·패드별 비아 수 (rf-06, rf-14)
- 보드 좌표계 ↔ 어셈블리 좌표계 변환 레코드와 사람 확정 절차 (rf-07)
- RF 사양 등록 — 안테나↔대역·기능 매핑표와 요구(최대 전력·SAR 한계·시험 이격·클리어런스 한계) (rf-33, rf-40)

