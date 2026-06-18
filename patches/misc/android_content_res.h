// Stub for the aconfig-generated <android_content_res.h>.
//
// Real builds run Android's aconfig codegen against
// frameworks/base/core/java/android/content/res/flags.aconfig to
// produce one C function per feature flag. We don't carry aconfig, so
// every flag here is force-disabled: the new code path the flag gates
// is skipped, and the legacy path (the one we already build cleanly)
// runs.
//
// If you bump AOSP_BRANCH and a new flag appears in flags.aconfig
// that's referenced in code we compile, add it here.

#pragma once

#define android_content_res_default_locale()                            false
#define android_content_res_font_scale_converter_public()               false
#define android_content_res_asset_file_descriptor_frro()                false
#define android_content_res_manifest_flagging()                         false
#define android_content_res_nine_patch_frro()                           false
#define android_content_res_register_resource_paths()                   false
#define android_content_res_handle_all_config_changes()                 false
#define android_content_res_dimension_frro()                            false
#define android_content_res_rro_constraints()                           false
#define android_content_res_rro_control_for_android_no_overlayable()    false
#define android_content_res_ignore_non_public_config_diff_for_resources_key() false
#define android_content_res_system_context_handle_app_info_changed()    false
#define android_content_res_layout_readwrite_flags()                    false
#define android_content_res_resource_readwrite_flags()                  false
#define android_content_res_resources_minor_version_support()           false
#define android_content_res_self_targeting_android_resource_frro()      false
#define android_content_res_always_false()                              false
#define android_content_res_test_flag_1()                               false
#define android_content_res_test_flag_2()                               false
#define android_content_res_test_flag_3()                               false
#define android_content_res_use_new_aconfig_storage()                   false
#define android_content_res_enhanced_debugging()                        false
#define android_content_res_idmap_crc_is_mtime()                        false
#define android_content_res_merge_idmap_binder_transactions()           false
#define android_content_res_xml_file_size_limit()                       false
