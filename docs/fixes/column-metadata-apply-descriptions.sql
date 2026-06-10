/* ---------------------------------------------------------------------------
 * Apply business_description values from the BCdataprod "Column Descriptions"
 * tab into CallCentre_SEM_STD_T.column_metadata.
 *
 * Source: BCdataprod.xlsx -> Column Descriptions tab (204 column dictionary).
 *
 * Strategy: keyed by column_name only (the source is flat, not per-table), so
 * one UPDATE per column_name applies the description across every table that
 * has a row for that column. UPDATEs apply when the existing description is:
 *   - NULL or whitespace, OR
 *   - the placeholder seeded by column-metadata-gap-report.sql
 *     ('TODO: business description for <column_name>').
 * Existing real descriptions are NOT overwritten.
 *
 * Run order:
 *   A. Preview count.
 *   B. Apply UPDATEs.
 *   C. Verify residual gaps.
 * ------------------------------------------------------------------------ */

/* --- A. Preview rows that will get a description -------------------- */
SELECT COUNT(*) AS rows_to_update
FROM   CallCentre_SEM_STD_T.column_metadata m
WHERE  m.column_name IN (
        'Seq', 'account_access_verification_avg_sim', 'account_access_verification_cnt', 'action_commitment_next_steps_avg_sim', 'action_commitment_next_steps_cnt', 'active_listening_avg_sim', 'active_listening_cnt', 'agent_average_streak_sec', 'agent_avg_turn_duration_ms', 'agent_avg_turn_words', 'agent_avg_word_length_chars', 'agent_disfluency_ratio', 'agent_end_sentiment', 'agent_intra_call_change_in_sentiment', 'agent_lexical_density', 'agent_longest_streak_sec', 'agent_longest_turn_duration_ms', 'agent_median_streak_sec', 'agent_median_turn_duration_ms', 'agent_overtalk_incidents', 'agent_overtalk_ms', 'agent_overtalk_ratio', 'agent_sentiment', 'agent_start_sentiment', 'agent_talk_ratio', 'agent_to_caller_wpm_ratio', 'agent_turn_count', 'agent_type_token_ratio', 'agent_wpm', 'agent_wpm_change', 'apology_or_regret_avg_sim', 'apology_or_regret_cnt', 'appropriate_questioning_technique_avg_sim', 'appropriate_questioning_technique_cnt', 'avg_pause_sec', 'avg_turn_duration_ms', 'avg_turn_words', 'avoidance_of_blame_or_deflection_avg_sim', 'avoidance_of_blame_or_deflection_cnt', 'avoidance_of_overpromise_avg_sim', 'avoidance_of_overpromise_cnt', 'avoiding_filler_or_uncertainty_avg_sim', 'avoiding_filler_or_uncertainty_cnt', 'avoiding_interruptions_avg_sim', 'avoiding_interruptions_cnt', 'avoiding_jargon_avg_sim', 'avoiding_jargon_cnt', 'avoiding_negativity_avg_sim', 'avoiding_negativity_cnt', 'billing_and_payment_discussion_avg_sim', 'billing_and_payment_discussion_cnt', 'brand_aligned_tone_avg_sim', 'brand_aligned_tone_cnt', 'call_change_in_sentiment', 'call_control_direction_avg_sim', 'call_control_direction_cnt', 'call_duration_sec', 'call_handling_all_hit', 'call_handling_avg_sim', 'call_handling_total_cnt', 'call_id', 'call_purpose_disclosure_avg_sim', 'call_purpose_disclosure_cnt', 'call_recording_disclosure_avg_sim', 'call_recording_disclosure_cnt', 'call_sentiment', 'caller_average_streak_sec', 'caller_avg_turn_duration_ms', 'caller_avg_turn_words', 'caller_avg_word_length_chars', 'caller_disfluency_ratio', 'caller_end_sentiment', 'caller_intra_call_change_in_sentiment', 'caller_lexical_density', 'caller_longest_streak_sec', 'caller_longest_turn_duration_ms', 'caller_median_streak_sec', 'caller_median_turn_duration_ms', 'caller_overtalk_incidents', 'caller_overtalk_ms', 'caller_overtalk_ratio', 'caller_sentiment', 'caller_start_sentiment', 'caller_talk_ratio', 'caller_turn_count', 'caller_type_token_ratio', 'caller_wpm', 'caller_wpm_change', 'calm_under_pressure_avg_sim', 'calm_under_pressure_cnt', 'case_logging_notetaking_avg_sim', 'case_logging_notetaking_cnt', 'clarification_questions_avg_sim', 'clarification_questions_cnt', 'communication_quality_all_hit', 'communication_quality_avg_sim', 'communication_quality_total_cnt', 'complaint_rights_avg_sim', 'complaint_rights_cnt', 'compliance_all_hit', 'compliance_avg_sim', 'compliance_total_cnt', 'concise_explanations_avg_sim', 'concise_explanations_cnt', 'conduct_and_professionalism_all_hit', 'conduct_and_professionalism_avg_sim', 'conduct_and_professionalism_total_cnt', 'confidence_and_reassurance_avg_sim', 'confidence_and_reassurance_cnt', 'confidence_building_avg_sim', 'confidence_building_cnt', 'confirmation_of_understanding_avg_sim', 'confirmation_of_understanding_cnt', 'consent_gathering_avg_sim', 'consent_gathering_cnt', 'conversation_summary', 'customer_appreciation_avg_sim', 'customer_appreciation_cnt', 'customer_centric_language_avg_sim', 'customer_centric_language_cnt', 'customer_experience_all_hit', 'customer_experience_avg_sim', 'customer_experience_total_cnt', 'de_escalation_avg_sim', 'de_escalation_cnt', 'empathetic_tone_avg_sim', 'empathetic_tone_cnt', 'empathy_statements_avg_sim', 'empathy_statements_cnt', 'end_sentiment', 'escalation_to_higher_tier_avg_sim', 'escalation_to_higher_tier_cnt', 'fee_charge_disclosure_avg_sim', 'fee_charge_disclosure_cnt', 'first_response_latency_sec', 'frustration_acknowledgement_avg_sim', 'frustration_acknowledgement_cnt', 'identity_verification_avg_sim', 'identity_verification_cnt', 'internal_handoff_transfer_avg_sim', 'internal_handoff_transfer_cnt', 'limitation_of_liability_avg_sim', 'limitation_of_liability_cnt', 'longest_turn_duration_ms', 'median_turn_duration_ms', 'order_placement_modification_avg_sim', 'order_placement_modification_cnt', 'overall_average_streak_sec', 'overall_avg_word_length_chars', 'overall_disfluency_ratio', 'overall_lexical_density', 'overall_longest_streak_sec', 'overall_median_streak_sec', 'overall_type_token_ratio', 'overtalk_incidents', 'overtalk_ms', 'overtalk_ratio', 'ownership_and_accountability_avg_sim', 'ownership_and_accountability_cnt', 'pacing_and_flow_control_avg_sim', 'pacing_and_flow_control_cnt', 'personalisation_contextualisation_avg_sim', 'personalisation_contextualisation_cnt', 'positive_framing_avg_sim', 'positive_framing_cnt', 'privacy_disclosure_avg_sim', 'privacy_disclosure_cnt', 'process_explanation_avg_sim', 'process_explanation_cnt', 'reassurance_and_support_avg_sim', 'reassurance_and_support_cnt', 'reframing_or_simplification_avg_sim', 'reframing_or_simplification_cnt', 'regulatory_obligations_avg_sim', 'regulatory_obligations_cnt', 'repetition_for_emphasis_avg_sim', 'repetition_for_emphasis_cnt', 'resolution_confirmation_avg_sim', 'resolution_confirmation_cnt', 'respectful_language_avg_sim', 'respectful_language_cnt', 'script_adherence_avg_sim', 'script_adherence_cnt', 'silence_incidents', 'silence_ratio', 'status_update_progress_report_avg_sim', 'status_update_progress_report_cnt', 'structured_signposting_avg_sim', 'structured_signposting_cnt', 'technical_troubleshooting_avg_sim', 'technical_troubleshooting_cnt', 'terms_and_conditions_explained_avg_sim', 'terms_and_conditions_explained_cnt', 'time_awareness_avg_sim', 'time_awareness_cnt', 'time_estimation_sla_mention_avg_sim', 'time_estimation_sla_mention_cnt', 'total_word_count', 'turn_count', 'turn_taking_avg_sim', 'turn_taking_cnt', 'words_per_min', 'wrap_up_summary_avg_sim', 'wrap_up_summary_cnt'
)
  AND  ( m.business_description IS NULL
      OR TRIM(m.business_description) = ''
      OR TRIM(m.business_description) = 'TODO: business description for ' || m.column_name );

/* --- B. Apply descriptions (one UPDATE per column_name) ----------- */
UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Sequential row index (0-based) for each call record'
WHERE  column_name = 'Seq'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for verifying account access'
WHERE  column_name = 'account_access_verification_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of account verification instances'
WHERE  column_name = 'account_access_verification_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for committing to actions and outlining next steps'
WHERE  column_name = 'action_commitment_next_steps_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of action commitment instances'
WHERE  column_name = 'action_commitment_next_steps_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for demonstrating active listening'
WHERE  column_name = 'active_listening_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of active listening instances'
WHERE  column_name = 'active_listening_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s average continuous speaking streak (sec)'
WHERE  column_name = 'agent_average_streak_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s average turn duration (ms)'
WHERE  column_name = 'agent_avg_turn_duration_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s average words per turn'
WHERE  column_name = 'agent_avg_turn_words'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s average word length'
WHERE  column_name = 'agent_avg_word_length_chars'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s disfluency ratio'
WHERE  column_name = 'agent_disfluency_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s sentiment at call end'
WHERE  column_name = 'agent_end_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Change in agent''s sentiment during call'
WHERE  column_name = 'agent_intra_call_change_in_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s lexical density'
WHERE  column_name = 'agent_lexical_density'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s longest speaking streak (sec)'
WHERE  column_name = 'agent_longest_streak_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s longest turn (ms)'
WHERE  column_name = 'agent_longest_turn_duration_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s median speaking streak (sec)'
WHERE  column_name = 'agent_median_streak_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s median turn duration (ms)'
WHERE  column_name = 'agent_median_turn_duration_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Number of times agent talked over caller'
WHERE  column_name = 'agent_overtalk_incidents'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total agent overtalk time (ms)'
WHERE  column_name = 'agent_overtalk_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Proportion of call with agent overtalk'
WHERE  column_name = 'agent_overtalk_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s overall sentiment'
WHERE  column_name = 'agent_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s sentiment at call start'
WHERE  column_name = 'agent_start_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Proportion of call time agent was speaking'
WHERE  column_name = 'agent_talk_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Ratio of agent WPM to caller WPM'
WHERE  column_name = 'agent_to_caller_wpm_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Number of turns by agent'
WHERE  column_name = 'agent_turn_count'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s vocabulary diversity'
WHERE  column_name = 'agent_type_token_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Agent''s speaking rate (words per minute)'
WHERE  column_name = 'agent_wpm'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Change in agent''s speaking rate during call'
WHERE  column_name = 'agent_wpm_change'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for expressing apology when appropriate'
WHERE  column_name = 'apology_or_regret_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of apology/regret instances'
WHERE  column_name = 'apology_or_regret_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for using proper questioning techniques'
WHERE  column_name = 'appropriate_questioning_technique_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of appropriate questioning instances'
WHERE  column_name = 'appropriate_questioning_technique_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Average pause duration (seconds)'
WHERE  column_name = 'avg_pause_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Average duration per turn (milliseconds)'
WHERE  column_name = 'avg_turn_duration_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Average words per turn'
WHERE  column_name = 'avg_turn_words'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for avoiding blame or deflection'
WHERE  column_name = 'avoidance_of_blame_or_deflection_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of blame avoidance instances'
WHERE  column_name = 'avoidance_of_blame_or_deflection_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for avoiding over-promising'
WHERE  column_name = 'avoidance_of_overpromise_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of overpromise avoidance instances'
WHERE  column_name = 'avoidance_of_overpromise_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for avoiding filler words/uncertainty'
WHERE  column_name = 'avoiding_filler_or_uncertainty_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of filler avoidance instances'
WHERE  column_name = 'avoiding_filler_or_uncertainty_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for avoiding interrupting the customer'
WHERE  column_name = 'avoiding_interruptions_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of interruption avoidance instances'
WHERE  column_name = 'avoiding_interruptions_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for avoiding technical jargon'
WHERE  column_name = 'avoiding_jargon_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of jargon avoidance instances'
WHERE  column_name = 'avoiding_jargon_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for maintaining positive tone, avoiding negativity'
WHERE  column_name = 'avoiding_negativity_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of negativity avoidance instances'
WHERE  column_name = 'avoiding_negativity_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for handling billing/payment topics'
WHERE  column_name = 'billing_and_payment_discussion_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of billing/payment discussion instances'
WHERE  column_name = 'billing_and_payment_discussion_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for using brand-appropriate tone'
WHERE  column_name = 'brand_aligned_tone_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of brand-aligned tone instances'
WHERE  column_name = 'brand_aligned_tone_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Change in sentiment from start to end of call'
WHERE  column_name = 'call_change_in_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for maintaining call control and direction'
WHERE  column_name = 'call_control_direction_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of call control instances'
WHERE  column_name = 'call_control_direction_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total call duration in seconds'
WHERE  column_name = 'call_duration_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = '1 if all call handling criteria met'
WHERE  column_name = 'call_handling_all_hit'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Overall call handling score'
WHERE  column_name = 'call_handling_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total count of call handling events'
WHERE  column_name = 'call_handling_total_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Unique identifier for each call/conversation'
WHERE  column_name = 'call_id'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for disclosing the call purpose'
WHERE  column_name = 'call_purpose_disclosure_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of purpose disclosure instances'
WHERE  column_name = 'call_purpose_disclosure_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for disclosing call recording'
WHERE  column_name = 'call_recording_disclosure_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of recording disclosure instances'
WHERE  column_name = 'call_recording_disclosure_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Overall sentiment of the call (-1=negative, 0=neutral, 1=positive)'
WHERE  column_name = 'call_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s average continuous speaking streak (sec)'
WHERE  column_name = 'caller_average_streak_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s average turn duration (ms)'
WHERE  column_name = 'caller_avg_turn_duration_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s average words per turn'
WHERE  column_name = 'caller_avg_turn_words'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s average word length'
WHERE  column_name = 'caller_avg_word_length_chars'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s disfluency ratio'
WHERE  column_name = 'caller_disfluency_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s sentiment at call end'
WHERE  column_name = 'caller_end_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Change in caller''s sentiment during call'
WHERE  column_name = 'caller_intra_call_change_in_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s lexical density'
WHERE  column_name = 'caller_lexical_density'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s longest speaking streak (sec)'
WHERE  column_name = 'caller_longest_streak_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s longest turn (ms)'
WHERE  column_name = 'caller_longest_turn_duration_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s median speaking streak (sec)'
WHERE  column_name = 'caller_median_streak_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s median turn duration (ms)'
WHERE  column_name = 'caller_median_turn_duration_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Number of times caller talked over agent'
WHERE  column_name = 'caller_overtalk_incidents'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total caller overtalk time (ms)'
WHERE  column_name = 'caller_overtalk_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Proportion of call with caller overtalk'
WHERE  column_name = 'caller_overtalk_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s overall sentiment'
WHERE  column_name = 'caller_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s sentiment at call start'
WHERE  column_name = 'caller_start_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Proportion of call time caller was speaking'
WHERE  column_name = 'caller_talk_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Number of turns by caller'
WHERE  column_name = 'caller_turn_count'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s vocabulary diversity'
WHERE  column_name = 'caller_type_token_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Caller''s speaking rate (words per minute)'
WHERE  column_name = 'caller_wpm'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Change in caller''s speaking rate during call'
WHERE  column_name = 'caller_wpm_change'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for maintaining calm demeanor under pressure'
WHERE  column_name = 'calm_under_pressure_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of calm under pressure instances'
WHERE  column_name = 'calm_under_pressure_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for documenting case notes'
WHERE  column_name = 'case_logging_notetaking_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of case logging/notetaking instances'
WHERE  column_name = 'case_logging_notetaking_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for asking clarifying questions'
WHERE  column_name = 'clarification_questions_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of clarification question instances'
WHERE  column_name = 'clarification_questions_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = '1 if all communication quality criteria met'
WHERE  column_name = 'communication_quality_all_hit'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Overall communication quality score'
WHERE  column_name = 'communication_quality_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total count of communication quality events'
WHERE  column_name = 'communication_quality_total_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for informing customer of complaint rights'
WHERE  column_name = 'complaint_rights_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of complaint rights mentions'
WHERE  column_name = 'complaint_rights_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = '1 if all compliance criteria met'
WHERE  column_name = 'compliance_all_hit'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Overall compliance score'
WHERE  column_name = 'compliance_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total count of compliance-related events'
WHERE  column_name = 'compliance_total_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for providing clear, concise explanations'
WHERE  column_name = 'concise_explanations_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of concise explanation instances'
WHERE  column_name = 'concise_explanations_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = '1 if all conduct/professionalism criteria met'
WHERE  column_name = 'conduct_and_professionalism_all_hit'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Overall conduct/professionalism score'
WHERE  column_name = 'conduct_and_professionalism_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total count of conduct/professionalism events'
WHERE  column_name = 'conduct_and_professionalism_total_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for projecting confidence and reassurance'
WHERE  column_name = 'confidence_and_reassurance_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of confidence/reassurance instances'
WHERE  column_name = 'confidence_and_reassurance_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for building customer confidence'
WHERE  column_name = 'confidence_building_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of confidence building instances'
WHERE  column_name = 'confidence_building_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for confirming understanding'
WHERE  column_name = 'confirmation_of_understanding_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of understanding confirmation instances'
WHERE  column_name = 'confirmation_of_understanding_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for gathering customer consent appropriately'
WHERE  column_name = 'consent_gathering_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of consent gathering instances'
WHERE  column_name = 'consent_gathering_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Transcript excerpt or summary of the call conversation with anonymized entities (e.g., [PERSON_NAME], [ORGANIZATION], [LOCATION])'
WHERE  column_name = 'conversation_summary'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for expressing appreciation to the customer'
WHERE  column_name = 'customer_appreciation_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of customer appreciation instances'
WHERE  column_name = 'customer_appreciation_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for using customer-focused language'
WHERE  column_name = 'customer_centric_language_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of customer-centric language instances'
WHERE  column_name = 'customer_centric_language_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = '1 if all customer experience criteria met'
WHERE  column_name = 'customer_experience_all_hit'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Overall customer experience score'
WHERE  column_name = 'customer_experience_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total count of customer experience events'
WHERE  column_name = 'customer_experience_total_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for de-escalating tense situations'
WHERE  column_name = 'de_escalation_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of de-escalation instances'
WHERE  column_name = 'de_escalation_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for demonstrating empathy in tone'
WHERE  column_name = 'empathetic_tone_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of empathetic tone instances'
WHERE  column_name = 'empathetic_tone_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for using empathy statements'
WHERE  column_name = 'empathy_statements_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of empathy statement instances'
WHERE  column_name = 'empathy_statements_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Sentiment at the end of the call'
WHERE  column_name = 'end_sentiment'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for handling escalations appropriately'
WHERE  column_name = 'escalation_to_higher_tier_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of escalation instances'
WHERE  column_name = 'escalation_to_higher_tier_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for disclosing fees/charges'
WHERE  column_name = 'fee_charge_disclosure_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of fee disclosure instances'
WHERE  column_name = 'fee_charge_disclosure_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Time until first response (seconds)'
WHERE  column_name = 'first_response_latency_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for acknowledging customer frustration'
WHERE  column_name = 'frustration_acknowledgement_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of frustration acknowledgement instances'
WHERE  column_name = 'frustration_acknowledgement_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for verifying caller identity'
WHERE  column_name = 'identity_verification_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of identity verification instances'
WHERE  column_name = 'identity_verification_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for handling internal transfers/handoffs'
WHERE  column_name = 'internal_handoff_transfer_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of internal transfer instances'
WHERE  column_name = 'internal_handoff_transfer_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for communicating liability limitations'
WHERE  column_name = 'limitation_of_liability_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of liability limitation instances'
WHERE  column_name = 'limitation_of_liability_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Longest single turn (milliseconds)'
WHERE  column_name = 'longest_turn_duration_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Median turn duration (milliseconds)'
WHERE  column_name = 'median_turn_duration_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for handling order placement/modifications'
WHERE  column_name = 'order_placement_modification_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of order placement/modification instances'
WHERE  column_name = 'order_placement_modification_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Average continuous speaking streak overall'
WHERE  column_name = 'overall_average_streak_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Average word length in characters (overall)'
WHERE  column_name = 'overall_avg_word_length_chars'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Ratio of disfluencies (um, uh, etc.) overall'
WHERE  column_name = 'overall_disfluency_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Ratio of content words to total words (overall)'
WHERE  column_name = 'overall_lexical_density'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Longest speaking streak overall'
WHERE  column_name = 'overall_longest_streak_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Median speaking streak overall'
WHERE  column_name = 'overall_median_streak_sec'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Vocabulary diversity measure (overall)'
WHERE  column_name = 'overall_type_token_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total number of overlapping speech instances'
WHERE  column_name = 'overtalk_incidents'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total overlapping speech duration (ms)'
WHERE  column_name = 'overtalk_ms'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Proportion of call with overlapping speech'
WHERE  column_name = 'overtalk_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for taking ownership and accountability'
WHERE  column_name = 'ownership_and_accountability_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of ownership/accountability instances'
WHERE  column_name = 'ownership_and_accountability_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for controlling pace and flow'
WHERE  column_name = 'pacing_and_flow_control_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of pacing control instances'
WHERE  column_name = 'pacing_and_flow_control_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for personalizing the interaction'
WHERE  column_name = 'personalisation_contextualisation_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of personalization instances'
WHERE  column_name = 'personalisation_contextualisation_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for framing information positively'
WHERE  column_name = 'positive_framing_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of positive framing instances'
WHERE  column_name = 'positive_framing_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for handling privacy disclosures'
WHERE  column_name = 'privacy_disclosure_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of privacy disclosure instances'
WHERE  column_name = 'privacy_disclosure_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for explaining processes clearly'
WHERE  column_name = 'process_explanation_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of process explanation instances'
WHERE  column_name = 'process_explanation_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for providing reassurance and emotional support'
WHERE  column_name = 'reassurance_and_support_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of reassurance/support instances'
WHERE  column_name = 'reassurance_and_support_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for reframing or simplifying complex info'
WHERE  column_name = 'reframing_or_simplification_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of reframing/simplification instances'
WHERE  column_name = 'reframing_or_simplification_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for adherence to regulatory/legal obligations'
WHERE  column_name = 'regulatory_obligations_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of regulatory obligation instances'
WHERE  column_name = 'regulatory_obligations_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for using repetition to emphasize key points'
WHERE  column_name = 'repetition_for_emphasis_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of emphasis repetition instances'
WHERE  column_name = 'repetition_for_emphasis_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for confirming issue resolution'
WHERE  column_name = 'resolution_confirmation_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of resolution confirmation instances'
WHERE  column_name = 'resolution_confirmation_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for using respectful and courteous language'
WHERE  column_name = 'respectful_language_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of respectful language instances'
WHERE  column_name = 'respectful_language_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for following required scripts'
WHERE  column_name = 'script_adherence_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of script adherence instances'
WHERE  column_name = 'script_adherence_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Number of silence periods in the call'
WHERE  column_name = 'silence_incidents'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Proportion of call that was silence'
WHERE  column_name = 'silence_ratio'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for providing status updates'
WHERE  column_name = 'status_update_progress_report_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of status update instances'
WHERE  column_name = 'status_update_progress_report_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for structured guidance through the call'
WHERE  column_name = 'structured_signposting_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of signposting instances'
WHERE  column_name = 'structured_signposting_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for technical troubleshooting guidance'
WHERE  column_name = 'technical_troubleshooting_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of troubleshooting instances'
WHERE  column_name = 'technical_troubleshooting_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for explaining terms and conditions'
WHERE  column_name = 'terms_and_conditions_explained_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of T&C explanation instances'
WHERE  column_name = 'terms_and_conditions_explained_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for demonstrating time awareness'
WHERE  column_name = 'time_awareness_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of time awareness instances'
WHERE  column_name = 'time_awareness_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for mentioning time estimates/SLAs'
WHERE  column_name = 'time_estimation_sla_mention_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of time/SLA mention instances'
WHERE  column_name = 'time_estimation_sla_mention_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total words spoken during the call'
WHERE  column_name = 'total_word_count'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Total number of conversational turns'
WHERE  column_name = 'turn_count'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for proper conversational turn-taking'
WHERE  column_name = 'turn_taking_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of turn-taking instances'
WHERE  column_name = 'turn_taking_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Overall speaking rate (words per minute)'
WHERE  column_name = 'words_per_min'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Avg score for providing a summary at call end'
WHERE  column_name = 'wrap_up_summary_avg_sim'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

UPDATE CallCentre_SEM_STD_T.column_metadata
SET    business_description = 'Count of wrap-up summary instances'
WHERE  column_name = 'wrap_up_summary_cnt'
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name );

/* --- C. Verify residual gaps (rows still missing a real description) ---- */
SELECT database_name, table_name, column_name, business_description
FROM   CallCentre_SEM_STD_T.column_metadata
WHERE  is_active = 1
  AND  ( business_description IS NULL
      OR TRIM(business_description) = ''
      OR TRIM(business_description) = 'TODO: business description for ' || column_name )
ORDER BY database_name, table_name, column_name;
