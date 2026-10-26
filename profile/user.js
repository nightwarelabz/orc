// orc — hardened defaults
// Seeded by the launcher into orc's own profile folder on
// first run only; the launcher never overwrites it afterwards.
// orc's profile is separate from every other browser:
//   Windows: %APPDATA%\orc\profile
//   macOS:   ~/Library/Application Support/orc/profile
//   Linux:   $XDG_DATA_HOME/orc/profile, else ~/.local/share/orc/profile
// Users can override anything below with user-overrides.js in the profile.

// --- home: Blacksite first, everything else still yours ---
user_pref("browser.startup.homepage", "https://nosuchmachine.net/");
user_pref("browser.startup.page", 1);
user_pref("browser.newtabpage.enabled", true);

// --- no phoning home ---
user_pref("toolkit.telemetry.enabled", false);
user_pref("toolkit.telemetry.unified", false);
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("browser.crashReports.unsubmittedCheck.autoSubmit2", false);
user_pref("app.shield.optoutstudies.enabled", false);
user_pref("browser.discovery.enabled", false);
user_pref("extensions.getAddons.cache.enabled", false);
user_pref("extensions.getAddons.showPane", false);

// --- tracking / fingerprinting ---
user_pref("privacy.trackingprotection.enabled", true);
user_pref("privacy.trackingprotection.socialtracking.enabled", true);
user_pref("privacy.trackingprotection.cryptomining.enabled", true);
user_pref("privacy.trackingprotection.fingerprinting.enabled", true);
user_pref("privacy.partition.network_state", true);
user_pref("privacy.query_stripping.enabled", true);
user_pref("privacy.query_stripping.strip_list", "__hsfp __hssc __hstc hsCtaTracking");
user_pref("network.cookie.cookieBehavior", 5); // dFPI / Total Cookie Protection
user_pref("privacy.resistFingerprinting", false); // Deliberate (Chase's full-functionality
                                                  // ruling, 2026-10-24): RFP normalizes canvas,
                                                  // timezone and timers in ways that break real
                                                  // sites. Tracking protection + Total Cookie
                                                  // Protection stay strict; flip RFP on in
                                                  // Settings if you want the harder posture.
user_pref("webgl.disabled", false);
// The engine-level autoconfig removes its additional per-site WebGL prompt
// for new and existing profiles (packaging/orc-autoconfig.cfg).

// --- https / safe browsing posture ---
user_pref("security.https_only_mode", true);
user_pref("security.https_only_mode_ever_enabled", true);
user_pref("network.stricttransportsecurity.preloadlist", true);
user_pref("security.cert_pinning.enforcement_level", 2);

// --- search: private by default, never sponsored ---
user_pref("browser.search.defaultenginename", "Tractor");
user_pref("browser.search.suggest.enabled", false);
user_pref("browser.urlbar.suggest.searches", false);
user_pref("browser.newtabpage.activity-stream.showSponsored", false);
user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);
user_pref("browser.newtabpage.activity-stream.feeds.section.topstories", false);

// --- annoyances off ---
user_pref("extensions.pocket.enabled", false);
user_pref("browser.vpn_promo.enabled", false);
user_pref("browser.promo.focus.enabled", false);
user_pref("identity.fxaccounts.enabled", false); // no account wall; enable manually if wanted

// --- media: everything plays ---
// The pinned engine defaults EME off, which silently breaks
// Netflix/Spotify-class sites. Full functionality means on.
// The CDM is a proprietary Google blob fetched on first use — that
// trade is stated in SECURITY.md, not hidden.
user_pref("media.eme.enabled", true);
user_pref("media.gmp-widevinecdm.enabled", true);
user_pref("media.gmp-widevinecdm.visible", true);

// --- downloads / files stay local ---
user_pref("browser.download.useDownloadDir", true);
user_pref("signon.rememberSignons", true);
