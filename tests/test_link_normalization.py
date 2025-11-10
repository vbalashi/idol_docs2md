from utils.link_normalization import strip_rel_and_ext, normalize_target_path, build_online_url, detect_doc_family_from_site_dir


def case(base_url, site_dir, raw_rel, expected_url, family=None, sub=None):
    p, a, ext = strip_rel_and_ext(raw_rel)
    fam = family or detect_doc_family_from_site_dir(site_dir)
    norm = normalize_target_path(p, fam)
    path_with_ext = f"{norm}{ext}" if ext else norm
    url = build_online_url(base_url, site_dir, path_with_ext, a, fam, sub)
    assert url == expected_url


def test_standard_encodings_variants():
    base = 'https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4'
    doc = 'Content_25.4_Documentation'
    expected = f"{base}/{doc}/Help/Content/Actions/ENCODINGS/_IDOL_ENCODINGS.htm"
    case(base, doc, '../../ENCODINGS/_IDOL_ENCODINGS.md', expected)
    case(base, doc, '../Actions/ENCODINGS/_IDOL_ENCODINGS.md', expected)


def test_standard_actions_prefix():
    base = 'https://example'
    doc = 'Content_25.4_Documentation'
    expected = f"{base}/{doc}/Help/Content/Actions/Query/Query.htm"
    case(base, doc, '../../Actions/Query/Query.htm', expected)


def test_idolserver_shared_admin():
    base = 'https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4'
    doc = 'IDOLServer_25.4_Documentation'
    sub = 'gettingstarted'
    expected = f"{base}/LicenseServer_25.4_Documentation/Help/Content/Shared_Admin/IDOLOperations/_ADM_SearchAndRetrieval.htm#Natural"
    case(base, doc, '../../Shared_Admin/IDOLOperations/_ADM_SearchAndRetrieval.htm#Natural', expected, sub=sub)


def test_idolserver_expert_page():
    base = 'https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4'
    doc = 'IDOLServer_25.4_Documentation'
    sub = 'expert'
    expected = f"{base}/{doc}/Guides/html/{sub}/Content/IDOLExpert/EnrichContent/Categorize_Documents.htm"
    case(base, doc, 'Content/IDOLExpert/EnrichContent/Categorize_Documents.htm', expected, sub=sub)


def test_lowercase_segments_are_canonicalized():
    base = 'https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4'
    doc = 'EductionGrammars_25.4_Documentation'
    expected = f"{base}/{doc}/Help/Content/GrammarReference/cc_bw.htm"
    case(base, doc, '../../grammarreference/cc_bw.htm', expected)


def test_explicit_html_extension_preserved():
    base = 'https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4'
    doc = 'Content_25.4_Documentation'
    expected = f"{base}/{doc}/Help/Content/Foo/Page.html"
    case(base, doc, '../../Content/Foo/Page.html', expected)
