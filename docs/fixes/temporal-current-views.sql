/* ---------------------------------------------------------------------------
 * CALLCENTRE-TEMPORAL-CURRENT-% — _Current view DDL kit
 *
 * One REPLACE VIEW per SCD2 entity. Each Current view:
 *   - selects from the corresponding _STD_V locking view (satisfies
 *     BUS_VIEW_SELECTS_TABLE_DIRECTLY by NOT touching _STD_T),
 *   - filters is_current = 1 AND is_deleted = 0,
 *   - omits the SCD2 control columns (valid_from_dts, valid_to_dts,
 *     is_current, is_deleted) from the projection so consumers see a
 *     clean "as of now" rowset.
 *
 * All columns are listed explicitly and aliased so consumers get a
 * stable mapping (per Coding Discipline).
 * ------------------------------------------------------------------------ */

REPLACE VIEW CallCentre_DOM_BUS_V.Agent_Current
(
      agent_id
    , agent_key
    , agent_name
    , source_agent_name
)
AS
LOCKING ROW FOR ACCESS
SELECT
      src.agent_id AS agent_id
    , src.agent_key AS agent_key
    , src.agent_name AS agent_name
    , src.source_agent_name AS source_agent_name
FROM CallCentre_DOM_STD_V.Agent_H AS src
WHERE is_current = 1 AND is_deleted = 0;

REPLACE VIEW CallCentre_DOM_BUS_V.Call_Current
(
      call_id
    , agent_id
    , start_hour
    , start_ts
    , day_of_week
)
AS
LOCKING ROW FOR ACCESS
SELECT
      src.call_id AS call_id
    , src.agent_id AS agent_id
    , src.start_hour AS start_hour
    , src.start_ts AS start_ts
    , src.day_of_week AS day_of_week
FROM CallCentre_DOM_STD_V.Call_H AS src
WHERE is_current = 1 AND is_deleted = 0;

REPLACE VIEW CallCentre_DOM_BUS_V.Call_Score_Current
(
      call_score_id
    , call_id
    , regulatory_obligations_avg_sim
    , privacy_disclosure_avg_sim
    , complaint_rights_avg_sim
    , terms_and_conditions_explained_avg_sim
    , consent_gathering_avg_sim
    , identity_verification_avg_sim
    , account_access_verification_avg_sim
    , script_adherence_avg_sim
    , fee_charge_disclosure_avg_sim
    , avoidance_of_overpromise_avg_sim
    , limitation_of_liability_avg_sim
    , call_recording_disclosure_avg_sim
    , customer_centric_language_avg_sim
    , reassurance_and_support_avg_sim
    , customer_appreciation_avg_sim
    , empathetic_tone_avg_sim
    , empathy_statements_avg_sim
    , positive_framing_avg_sim
    , avoiding_negativity_avg_sim
    , avoidance_of_blame_or_deflection_avg_sim
    , apology_or_regret_avg_sim
    , respectful_language_avg_sim
    , personalisation_contextualisation_avg_sim
    , frustration_acknowledgement_avg_sim
    , brand_aligned_tone_avg_sim
    , active_listening_avg_sim
    , avoiding_interruptions_avg_sim
    , turn_taking_avg_sim
    , clarification_questions_avg_sim
    , appropriate_questioning_technique_avg_sim
    , concise_explanations_avg_sim
    , avoiding_jargon_avg_sim
    , process_explanation_avg_sim
    , structured_signposting_avg_sim
    , repetition_for_emphasis_avg_sim
    , confirmation_of_understanding_avg_sim
    , reframing_or_simplification_avg_sim
    , pacing_and_flow_control_avg_sim
    , avoiding_filler_or_uncertainty_avg_sim
    , resolution_confirmation_avg_sim
    , action_commitment_next_steps_avg_sim
    , wrap_up_summary_avg_sim
    , case_logging_notetaking_avg_sim
    , order_placement_modification_avg_sim
    , ownership_and_accountability_avg_sim
    , time_estimation_sla_mention_avg_sim
    , status_update_progress_report_avg_sim
    , time_awareness_avg_sim
    , de_escalation_avg_sim
    , calm_under_pressure_avg_sim
    , confidence_and_reassurance_avg_sim
    , confidence_building_avg_sim
    , internal_handoff_transfer_avg_sim
    , escalation_to_higher_tier_avg_sim
    , billing_and_payment_discussion_avg_sim
    , call_control_direction_avg_sim
    , call_purpose_disclosure_avg_sim
    , technical_troubleshooting_avg_sim
)
AS
LOCKING ROW FOR ACCESS
SELECT
      src.call_score_id AS call_score_id
    , src.call_id AS call_id
    , src.regulatory_obligations_avg_sim AS regulatory_obligations_avg_sim
    , src.privacy_disclosure_avg_sim AS privacy_disclosure_avg_sim
    , src.complaint_rights_avg_sim AS complaint_rights_avg_sim
    , src.terms_and_conditions_explained_avg_sim AS terms_and_conditions_explained_avg_sim
    , src.consent_gathering_avg_sim AS consent_gathering_avg_sim
    , src.identity_verification_avg_sim AS identity_verification_avg_sim
    , src.account_access_verification_avg_sim AS account_access_verification_avg_sim
    , src.script_adherence_avg_sim AS script_adherence_avg_sim
    , src.fee_charge_disclosure_avg_sim AS fee_charge_disclosure_avg_sim
    , src.avoidance_of_overpromise_avg_sim AS avoidance_of_overpromise_avg_sim
    , src.limitation_of_liability_avg_sim AS limitation_of_liability_avg_sim
    , src.call_recording_disclosure_avg_sim AS call_recording_disclosure_avg_sim
    , src.customer_centric_language_avg_sim AS customer_centric_language_avg_sim
    , src.reassurance_and_support_avg_sim AS reassurance_and_support_avg_sim
    , src.customer_appreciation_avg_sim AS customer_appreciation_avg_sim
    , src.empathetic_tone_avg_sim AS empathetic_tone_avg_sim
    , src.empathy_statements_avg_sim AS empathy_statements_avg_sim
    , src.positive_framing_avg_sim AS positive_framing_avg_sim
    , src.avoiding_negativity_avg_sim AS avoiding_negativity_avg_sim
    , src.avoidance_of_blame_or_deflection_avg_sim AS avoidance_of_blame_or_deflection_avg_sim
    , src.apology_or_regret_avg_sim AS apology_or_regret_avg_sim
    , src.respectful_language_avg_sim AS respectful_language_avg_sim
    , src.personalisation_contextualisation_avg_sim AS personalisation_contextualisation_avg_sim
    , src.frustration_acknowledgement_avg_sim AS frustration_acknowledgement_avg_sim
    , src.brand_aligned_tone_avg_sim AS brand_aligned_tone_avg_sim
    , src.active_listening_avg_sim AS active_listening_avg_sim
    , src.avoiding_interruptions_avg_sim AS avoiding_interruptions_avg_sim
    , src.turn_taking_avg_sim AS turn_taking_avg_sim
    , src.clarification_questions_avg_sim AS clarification_questions_avg_sim
    , src.appropriate_questioning_technique_avg_sim AS appropriate_questioning_technique_avg_sim
    , src.concise_explanations_avg_sim AS concise_explanations_avg_sim
    , src.avoiding_jargon_avg_sim AS avoiding_jargon_avg_sim
    , src.process_explanation_avg_sim AS process_explanation_avg_sim
    , src.structured_signposting_avg_sim AS structured_signposting_avg_sim
    , src.repetition_for_emphasis_avg_sim AS repetition_for_emphasis_avg_sim
    , src.confirmation_of_understanding_avg_sim AS confirmation_of_understanding_avg_sim
    , src.reframing_or_simplification_avg_sim AS reframing_or_simplification_avg_sim
    , src.pacing_and_flow_control_avg_sim AS pacing_and_flow_control_avg_sim
    , src.avoiding_filler_or_uncertainty_avg_sim AS avoiding_filler_or_uncertainty_avg_sim
    , src.resolution_confirmation_avg_sim AS resolution_confirmation_avg_sim
    , src.action_commitment_next_steps_avg_sim AS action_commitment_next_steps_avg_sim
    , src.wrap_up_summary_avg_sim AS wrap_up_summary_avg_sim
    , src.case_logging_notetaking_avg_sim AS case_logging_notetaking_avg_sim
    , src.order_placement_modification_avg_sim AS order_placement_modification_avg_sim
    , src.ownership_and_accountability_avg_sim AS ownership_and_accountability_avg_sim
    , src.time_estimation_sla_mention_avg_sim AS time_estimation_sla_mention_avg_sim
    , src.status_update_progress_report_avg_sim AS status_update_progress_report_avg_sim
    , src.time_awareness_avg_sim AS time_awareness_avg_sim
    , src.de_escalation_avg_sim AS de_escalation_avg_sim
    , src.calm_under_pressure_avg_sim AS calm_under_pressure_avg_sim
    , src.confidence_and_reassurance_avg_sim AS confidence_and_reassurance_avg_sim
    , src.confidence_building_avg_sim AS confidence_building_avg_sim
    , src.internal_handoff_transfer_avg_sim AS internal_handoff_transfer_avg_sim
    , src.escalation_to_higher_tier_avg_sim AS escalation_to_higher_tier_avg_sim
    , src.billing_and_payment_discussion_avg_sim AS billing_and_payment_discussion_avg_sim
    , src.call_control_direction_avg_sim AS call_control_direction_avg_sim
    , src.call_purpose_disclosure_avg_sim AS call_purpose_disclosure_avg_sim
    , src.technical_troubleshooting_avg_sim AS technical_troubleshooting_avg_sim
FROM CallCentre_DOM_STD_V.Call_Score_H AS src
WHERE is_current = 1 AND is_deleted = 0;

REPLACE VIEW CallCentre_DOM_BUS_V.Call_Score_Cnt_Current
(
      call_score_cnt_id
    , call_id
    , regulatory_obligations_cnt
    , privacy_disclosure_cnt
    , complaint_rights_cnt
    , terms_and_conditions_explained_cnt
    , consent_gathering_cnt
    , identity_verification_cnt
    , account_access_verification_cnt
    , script_adherence_cnt
    , fee_charge_disclosure_cnt
    , avoidance_of_overpromise_cnt
    , limitation_of_liability_cnt
    , call_recording_disclosure_cnt
    , customer_centric_language_cnt
    , reassurance_and_support_cnt
    , customer_appreciation_cnt
    , empathetic_tone_cnt
    , empathy_statements_cnt
    , positive_framing_cnt
    , avoiding_negativity_cnt
    , avoidance_of_blame_or_deflection_cnt
    , apology_or_regret_cnt
    , respectful_language_cnt
    , personalisation_contextualisation_cnt
    , frustration_acknowledgement_cnt
    , brand_aligned_tone_cnt
    , active_listening_cnt
    , avoiding_interruptions_cnt
    , turn_taking_cnt
    , clarification_questions_cnt
    , appropriate_questioning_technique_cnt
    , concise_explanations_cnt
    , avoiding_jargon_cnt
    , process_explanation_cnt
    , structured_signposting_cnt
    , repetition_for_emphasis_cnt
    , confirmation_of_understanding_cnt
    , reframing_or_simplification_cnt
    , pacing_and_flow_control_cnt
    , avoiding_filler_or_uncertainty_cnt
    , resolution_confirmation_cnt
    , action_commitment_next_steps_cnt
    , wrap_up_summary_cnt
    , case_logging_notetaking_cnt
    , order_placement_modification_cnt
    , ownership_and_accountability_cnt
    , time_estimation_sla_mention_cnt
    , status_update_progress_report_cnt
    , time_awareness_cnt
    , de_escalation_cnt
    , calm_under_pressure_cnt
    , confidence_and_reassurance_cnt
    , confidence_building_cnt
    , internal_handoff_transfer_cnt
    , escalation_to_higher_tier_cnt
    , billing_and_payment_discussion_cnt
    , call_control_direction_cnt
    , call_purpose_disclosure_cnt
    , technical_troubleshooting_cnt
)
AS
LOCKING ROW FOR ACCESS
SELECT
      src.call_score_cnt_id AS call_score_cnt_id
    , src.call_id AS call_id
    , src.regulatory_obligations_cnt AS regulatory_obligations_cnt
    , src.privacy_disclosure_cnt AS privacy_disclosure_cnt
    , src.complaint_rights_cnt AS complaint_rights_cnt
    , src.terms_and_conditions_explained_cnt AS terms_and_conditions_explained_cnt
    , src.consent_gathering_cnt AS consent_gathering_cnt
    , src.identity_verification_cnt AS identity_verification_cnt
    , src.account_access_verification_cnt AS account_access_verification_cnt
    , src.script_adherence_cnt AS script_adherence_cnt
    , src.fee_charge_disclosure_cnt AS fee_charge_disclosure_cnt
    , src.avoidance_of_overpromise_cnt AS avoidance_of_overpromise_cnt
    , src.limitation_of_liability_cnt AS limitation_of_liability_cnt
    , src.call_recording_disclosure_cnt AS call_recording_disclosure_cnt
    , src.customer_centric_language_cnt AS customer_centric_language_cnt
    , src.reassurance_and_support_cnt AS reassurance_and_support_cnt
    , src.customer_appreciation_cnt AS customer_appreciation_cnt
    , src.empathetic_tone_cnt AS empathetic_tone_cnt
    , src.empathy_statements_cnt AS empathy_statements_cnt
    , src.positive_framing_cnt AS positive_framing_cnt
    , src.avoiding_negativity_cnt AS avoiding_negativity_cnt
    , src.avoidance_of_blame_or_deflection_cnt AS avoidance_of_blame_or_deflection_cnt
    , src.apology_or_regret_cnt AS apology_or_regret_cnt
    , src.respectful_language_cnt AS respectful_language_cnt
    , src.personalisation_contextualisation_cnt AS personalisation_contextualisation_cnt
    , src.frustration_acknowledgement_cnt AS frustration_acknowledgement_cnt
    , src.brand_aligned_tone_cnt AS brand_aligned_tone_cnt
    , src.active_listening_cnt AS active_listening_cnt
    , src.avoiding_interruptions_cnt AS avoiding_interruptions_cnt
    , src.turn_taking_cnt AS turn_taking_cnt
    , src.clarification_questions_cnt AS clarification_questions_cnt
    , src.appropriate_questioning_technique_cnt AS appropriate_questioning_technique_cnt
    , src.concise_explanations_cnt AS concise_explanations_cnt
    , src.avoiding_jargon_cnt AS avoiding_jargon_cnt
    , src.process_explanation_cnt AS process_explanation_cnt
    , src.structured_signposting_cnt AS structured_signposting_cnt
    , src.repetition_for_emphasis_cnt AS repetition_for_emphasis_cnt
    , src.confirmation_of_understanding_cnt AS confirmation_of_understanding_cnt
    , src.reframing_or_simplification_cnt AS reframing_or_simplification_cnt
    , src.pacing_and_flow_control_cnt AS pacing_and_flow_control_cnt
    , src.avoiding_filler_or_uncertainty_cnt AS avoiding_filler_or_uncertainty_cnt
    , src.resolution_confirmation_cnt AS resolution_confirmation_cnt
    , src.action_commitment_next_steps_cnt AS action_commitment_next_steps_cnt
    , src.wrap_up_summary_cnt AS wrap_up_summary_cnt
    , src.case_logging_notetaking_cnt AS case_logging_notetaking_cnt
    , src.order_placement_modification_cnt AS order_placement_modification_cnt
    , src.ownership_and_accountability_cnt AS ownership_and_accountability_cnt
    , src.time_estimation_sla_mention_cnt AS time_estimation_sla_mention_cnt
    , src.status_update_progress_report_cnt AS status_update_progress_report_cnt
    , src.time_awareness_cnt AS time_awareness_cnt
    , src.de_escalation_cnt AS de_escalation_cnt
    , src.calm_under_pressure_cnt AS calm_under_pressure_cnt
    , src.confidence_and_reassurance_cnt AS confidence_and_reassurance_cnt
    , src.confidence_building_cnt AS confidence_building_cnt
    , src.internal_handoff_transfer_cnt AS internal_handoff_transfer_cnt
    , src.escalation_to_higher_tier_cnt AS escalation_to_higher_tier_cnt
    , src.billing_and_payment_discussion_cnt AS billing_and_payment_discussion_cnt
    , src.call_control_direction_cnt AS call_control_direction_cnt
    , src.call_purpose_disclosure_cnt AS call_purpose_disclosure_cnt
    , src.technical_troubleshooting_cnt AS technical_troubleshooting_cnt
FROM CallCentre_DOM_STD_V.Call_Score_Cnt_H AS src
WHERE is_current = 1 AND is_deleted = 0;

REPLACE VIEW CallCentre_DOM_BUS_V.Call_Dynamics_Current
(
      call_dynamics_id
    , call_id
    , call_duration_sec
    , total_word_count
    , words_per_min
    , first_response_latency_sec
    , turn_count
    , avg_turn_duration_ms
    , median_turn_duration_ms
    , longest_turn_duration_ms
    , avg_turn_words
    , agent_turn_count
    , agent_avg_turn_duration_ms
    , agent_median_turn_duration_ms
    , agent_longest_turn_duration_ms
    , agent_avg_turn_words
    , caller_turn_count
    , caller_avg_turn_duration_ms
    , caller_median_turn_duration_ms
    , caller_longest_turn_duration_ms
    , caller_avg_turn_words
    , agent_talk_ratio
    , caller_talk_ratio
    , agent_wpm
    , caller_wpm
    , agent_to_caller_wpm_ratio
    , silence_incidents
    , silence_ratio
    , avg_pause_sec
    , overall_lexical_density
    , overall_type_token_ratio
    , overall_avg_word_length_chars
    , overall_disfluency_ratio
    , agent_lexical_density
    , agent_type_token_ratio
    , agent_avg_word_length_chars
    , agent_disfluency_ratio
    , caller_lexical_density
    , caller_type_token_ratio
    , caller_avg_word_length_chars
    , caller_disfluency_ratio
    , agent_average_streak_sec
    , agent_median_streak_sec
    , agent_longest_streak_sec
    , caller_average_streak_sec
    , caller_median_streak_sec
    , caller_longest_streak_sec
    , overall_average_streak_sec
    , overall_median_streak_sec
    , overall_longest_streak_sec
    , agent_wpm_change
    , caller_wpm_change
    , overtalk_incidents
    , overtalk_ms
    , overtalk_ratio
    , agent_overtalk_incidents
    , agent_overtalk_ms
    , agent_overtalk_ratio
    , caller_overtalk_incidents
    , caller_overtalk_ms
    , caller_overtalk_ratio
    , call_sentiment
    , end_sentiment
    , call_change_in_sentiment
    , agent_sentiment
    , agent_start_sentiment
    , agent_end_sentiment
    , agent_intra_call_change_in_sentiment
    , caller_sentiment
    , caller_start_sentiment
    , caller_end_sentiment
    , caller_intra_call_change_in_sentiment
)
AS
LOCKING ROW FOR ACCESS
SELECT
      src.call_dynamics_id AS call_dynamics_id
    , src.call_id AS call_id
    , src.call_duration_sec AS call_duration_sec
    , src.total_word_count AS total_word_count
    , src.words_per_min AS words_per_min
    , src.first_response_latency_sec AS first_response_latency_sec
    , src.turn_count AS turn_count
    , src.avg_turn_duration_ms AS avg_turn_duration_ms
    , src.median_turn_duration_ms AS median_turn_duration_ms
    , src.longest_turn_duration_ms AS longest_turn_duration_ms
    , src.avg_turn_words AS avg_turn_words
    , src.agent_turn_count AS agent_turn_count
    , src.agent_avg_turn_duration_ms AS agent_avg_turn_duration_ms
    , src.agent_median_turn_duration_ms AS agent_median_turn_duration_ms
    , src.agent_longest_turn_duration_ms AS agent_longest_turn_duration_ms
    , src.agent_avg_turn_words AS agent_avg_turn_words
    , src.caller_turn_count AS caller_turn_count
    , src.caller_avg_turn_duration_ms AS caller_avg_turn_duration_ms
    , src.caller_median_turn_duration_ms AS caller_median_turn_duration_ms
    , src.caller_longest_turn_duration_ms AS caller_longest_turn_duration_ms
    , src.caller_avg_turn_words AS caller_avg_turn_words
    , src.agent_talk_ratio AS agent_talk_ratio
    , src.caller_talk_ratio AS caller_talk_ratio
    , src.agent_wpm AS agent_wpm
    , src.caller_wpm AS caller_wpm
    , src.agent_to_caller_wpm_ratio AS agent_to_caller_wpm_ratio
    , src.silence_incidents AS silence_incidents
    , src.silence_ratio AS silence_ratio
    , src.avg_pause_sec AS avg_pause_sec
    , src.overall_lexical_density AS overall_lexical_density
    , src.overall_type_token_ratio AS overall_type_token_ratio
    , src.overall_avg_word_length_chars AS overall_avg_word_length_chars
    , src.overall_disfluency_ratio AS overall_disfluency_ratio
    , src.agent_lexical_density AS agent_lexical_density
    , src.agent_type_token_ratio AS agent_type_token_ratio
    , src.agent_avg_word_length_chars AS agent_avg_word_length_chars
    , src.agent_disfluency_ratio AS agent_disfluency_ratio
    , src.caller_lexical_density AS caller_lexical_density
    , src.caller_type_token_ratio AS caller_type_token_ratio
    , src.caller_avg_word_length_chars AS caller_avg_word_length_chars
    , src.caller_disfluency_ratio AS caller_disfluency_ratio
    , src.agent_average_streak_sec AS agent_average_streak_sec
    , src.agent_median_streak_sec AS agent_median_streak_sec
    , src.agent_longest_streak_sec AS agent_longest_streak_sec
    , src.caller_average_streak_sec AS caller_average_streak_sec
    , src.caller_median_streak_sec AS caller_median_streak_sec
    , src.caller_longest_streak_sec AS caller_longest_streak_sec
    , src.overall_average_streak_sec AS overall_average_streak_sec
    , src.overall_median_streak_sec AS overall_median_streak_sec
    , src.overall_longest_streak_sec AS overall_longest_streak_sec
    , src.agent_wpm_change AS agent_wpm_change
    , src.caller_wpm_change AS caller_wpm_change
    , src.overtalk_incidents AS overtalk_incidents
    , src.overtalk_ms AS overtalk_ms
    , src.overtalk_ratio AS overtalk_ratio
    , src.agent_overtalk_incidents AS agent_overtalk_incidents
    , src.agent_overtalk_ms AS agent_overtalk_ms
    , src.agent_overtalk_ratio AS agent_overtalk_ratio
    , src.caller_overtalk_incidents AS caller_overtalk_incidents
    , src.caller_overtalk_ms AS caller_overtalk_ms
    , src.caller_overtalk_ratio AS caller_overtalk_ratio
    , src.call_sentiment AS call_sentiment
    , src.end_sentiment AS end_sentiment
    , src.call_change_in_sentiment AS call_change_in_sentiment
    , src.agent_sentiment AS agent_sentiment
    , src.agent_start_sentiment AS agent_start_sentiment
    , src.agent_end_sentiment AS agent_end_sentiment
    , src.agent_intra_call_change_in_sentiment AS agent_intra_call_change_in_sentiment
    , src.caller_sentiment AS caller_sentiment
    , src.caller_start_sentiment AS caller_start_sentiment
    , src.caller_end_sentiment AS caller_end_sentiment
    , src.caller_intra_call_change_in_sentiment AS caller_intra_call_change_in_sentiment
FROM CallCentre_DOM_STD_V.Call_Dynamics_H AS src
WHERE is_current = 1 AND is_deleted = 0;

REPLACE VIEW CallCentre_DOM_BUS_V.Call_Category_Score_Current
(
      call_category_score_id
    , call_id
    , communication_quality_avg_sim
    , conduct_and_professionalism_avg_sim
    , customer_experience_avg_sim
    , compliance_avg_sim
    , call_handling_avg_sim
    , communication_quality_total_cnt
    , conduct_and_professionalism_total_cnt
    , customer_experience_total_cnt
    , compliance_total_cnt
    , call_handling_total_cnt
    , communication_quality_all_hit
    , conduct_and_professionalism_all_hit
    , customer_experience_all_hit
    , compliance_all_hit
    , call_handling_all_hit
)
AS
LOCKING ROW FOR ACCESS
SELECT
      src.call_category_score_id AS call_category_score_id
    , src.call_id AS call_id
    , src.communication_quality_avg_sim AS communication_quality_avg_sim
    , src.conduct_and_professionalism_avg_sim AS conduct_and_professionalism_avg_sim
    , src.customer_experience_avg_sim AS customer_experience_avg_sim
    , src.compliance_avg_sim AS compliance_avg_sim
    , src.call_handling_avg_sim AS call_handling_avg_sim
    , src.communication_quality_total_cnt AS communication_quality_total_cnt
    , src.conduct_and_professionalism_total_cnt AS conduct_and_professionalism_total_cnt
    , src.customer_experience_total_cnt AS customer_experience_total_cnt
    , src.compliance_total_cnt AS compliance_total_cnt
    , src.call_handling_total_cnt AS call_handling_total_cnt
    , src.communication_quality_all_hit AS communication_quality_all_hit
    , src.conduct_and_professionalism_all_hit AS conduct_and_professionalism_all_hit
    , src.customer_experience_all_hit AS customer_experience_all_hit
    , src.compliance_all_hit AS compliance_all_hit
    , src.call_handling_all_hit AS call_handling_all_hit
FROM CallCentre_DOM_STD_V.Call_Category_Score_H AS src
WHERE is_current = 1 AND is_deleted = 0;

REPLACE VIEW CallCentre_PRE_BUS_V.call_features_current
(
      feature_group_id
    , call_id
    , entity_type
    , regulatory_obligations_norm
    , privacy_disclosure_norm
    , complaint_rights_norm
    , terms_and_conditions_explained_norm
    , consent_gathering_norm
    , identity_verification_norm
    , account_access_verification_norm
    , script_adherence_norm
    , fee_charge_disclosure_norm
    , avoidance_of_overpromise_norm
    , limitation_of_liability_norm
    , call_recording_disclosure_norm
    , customer_centric_language_norm
    , reassurance_and_support_norm
    , customer_appreciation_norm
    , empathetic_tone_norm
    , empathy_statements_norm
    , positive_framing_norm
    , avoiding_negativity_norm
    , avoidance_of_blame_or_deflection_norm
    , apology_or_regret_norm
    , respectful_language_norm
    , personalisation_contextualisation_norm
    , frustration_acknowledgement_norm
    , brand_aligned_tone_norm
    , active_listening_norm
    , avoiding_interruptions_norm
    , turn_taking_norm
    , clarification_questions_norm
    , appropriate_questioning_technique_norm
    , concise_explanations_norm
    , avoiding_jargon_norm
    , process_explanation_norm
    , structured_signposting_norm
    , repetition_for_emphasis_norm
    , confirmation_of_understanding_norm
    , reframing_or_simplification_norm
    , pacing_and_flow_control_norm
    , avoiding_filler_or_uncertainty_norm
    , resolution_confirmation_norm
    , action_commitment_next_steps_norm
    , wrap_up_summary_norm
    , case_logging_notetaking_norm
    , order_placement_modification_norm
    , ownership_and_accountability_norm
    , time_estimation_sla_mention_norm
    , status_update_progress_report_norm
    , time_awareness_norm
    , de_escalation_norm
    , calm_under_pressure_norm
    , confidence_and_reassurance_norm
    , confidence_building_norm
    , internal_handoff_transfer_norm
    , escalation_to_higher_tier_norm
    , billing_and_payment_discussion_norm
    , call_control_direction_norm
    , call_purpose_disclosure_norm
    , technical_troubleshooting_norm
    , compliance_composite_score
    , cx_composite_score
    , communication_composite_score
    , resolution_composite_score
    , difficult_situations_composite_score
    , overall_quality_score
    , feature_group_name
    , feature_group_version
    , observation_dts
    , computation_dts
    , source_system
    , created_by
)
AS
LOCKING ROW FOR ACCESS
SELECT
      src.feature_group_id AS feature_group_id
    , src.call_id AS call_id
    , src.entity_type AS entity_type
    , src.regulatory_obligations_norm AS regulatory_obligations_norm
    , src.privacy_disclosure_norm AS privacy_disclosure_norm
    , src.complaint_rights_norm AS complaint_rights_norm
    , src.terms_and_conditions_explained_norm AS terms_and_conditions_explained_norm
    , src.consent_gathering_norm AS consent_gathering_norm
    , src.identity_verification_norm AS identity_verification_norm
    , src.account_access_verification_norm AS account_access_verification_norm
    , src.script_adherence_norm AS script_adherence_norm
    , src.fee_charge_disclosure_norm AS fee_charge_disclosure_norm
    , src.avoidance_of_overpromise_norm AS avoidance_of_overpromise_norm
    , src.limitation_of_liability_norm AS limitation_of_liability_norm
    , src.call_recording_disclosure_norm AS call_recording_disclosure_norm
    , src.customer_centric_language_norm AS customer_centric_language_norm
    , src.reassurance_and_support_norm AS reassurance_and_support_norm
    , src.customer_appreciation_norm AS customer_appreciation_norm
    , src.empathetic_tone_norm AS empathetic_tone_norm
    , src.empathy_statements_norm AS empathy_statements_norm
    , src.positive_framing_norm AS positive_framing_norm
    , src.avoiding_negativity_norm AS avoiding_negativity_norm
    , src.avoidance_of_blame_or_deflection_norm AS avoidance_of_blame_or_deflection_norm
    , src.apology_or_regret_norm AS apology_or_regret_norm
    , src.respectful_language_norm AS respectful_language_norm
    , src.personalisation_contextualisation_norm AS personalisation_contextualisation_norm
    , src.frustration_acknowledgement_norm AS frustration_acknowledgement_norm
    , src.brand_aligned_tone_norm AS brand_aligned_tone_norm
    , src.active_listening_norm AS active_listening_norm
    , src.avoiding_interruptions_norm AS avoiding_interruptions_norm
    , src.turn_taking_norm AS turn_taking_norm
    , src.clarification_questions_norm AS clarification_questions_norm
    , src.appropriate_questioning_technique_norm AS appropriate_questioning_technique_norm
    , src.concise_explanations_norm AS concise_explanations_norm
    , src.avoiding_jargon_norm AS avoiding_jargon_norm
    , src.process_explanation_norm AS process_explanation_norm
    , src.structured_signposting_norm AS structured_signposting_norm
    , src.repetition_for_emphasis_norm AS repetition_for_emphasis_norm
    , src.confirmation_of_understanding_norm AS confirmation_of_understanding_norm
    , src.reframing_or_simplification_norm AS reframing_or_simplification_norm
    , src.pacing_and_flow_control_norm AS pacing_and_flow_control_norm
    , src.avoiding_filler_or_uncertainty_norm AS avoiding_filler_or_uncertainty_norm
    , src.resolution_confirmation_norm AS resolution_confirmation_norm
    , src.action_commitment_next_steps_norm AS action_commitment_next_steps_norm
    , src.wrap_up_summary_norm AS wrap_up_summary_norm
    , src.case_logging_notetaking_norm AS case_logging_notetaking_norm
    , src.order_placement_modification_norm AS order_placement_modification_norm
    , src.ownership_and_accountability_norm AS ownership_and_accountability_norm
    , src.time_estimation_sla_mention_norm AS time_estimation_sla_mention_norm
    , src.status_update_progress_report_norm AS status_update_progress_report_norm
    , src.time_awareness_norm AS time_awareness_norm
    , src.de_escalation_norm AS de_escalation_norm
    , src.calm_under_pressure_norm AS calm_under_pressure_norm
    , src.confidence_and_reassurance_norm AS confidence_and_reassurance_norm
    , src.confidence_building_norm AS confidence_building_norm
    , src.internal_handoff_transfer_norm AS internal_handoff_transfer_norm
    , src.escalation_to_higher_tier_norm AS escalation_to_higher_tier_norm
    , src.billing_and_payment_discussion_norm AS billing_and_payment_discussion_norm
    , src.call_control_direction_norm AS call_control_direction_norm
    , src.call_purpose_disclosure_norm AS call_purpose_disclosure_norm
    , src.technical_troubleshooting_norm AS technical_troubleshooting_norm
    , src.compliance_composite_score AS compliance_composite_score
    , src.cx_composite_score AS cx_composite_score
    , src.communication_composite_score AS communication_composite_score
    , src.resolution_composite_score AS resolution_composite_score
    , src.difficult_situations_composite_score AS difficult_situations_composite_score
    , src.overall_quality_score AS overall_quality_score
    , src.feature_group_name AS feature_group_name
    , src.feature_group_version AS feature_group_version
    , src.observation_dts AS observation_dts
    , src.computation_dts AS computation_dts
    , src.source_system AS source_system
    , src.created_by AS created_by
FROM CallCentre_PRE_STD_V.call_behaviour_features AS src
WHERE is_current = 1;

