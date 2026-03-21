# frozen_string_literal: true

require 'test_helper'
require 'tempfile'

class TestmondaiQualityAuditServiceTest < ActiveSupport::TestCase
  test 'detects short explanation duplicate choices and invalid seikai' do
    csv = Tempfile.new(['audit', '.csv'])
    csv.write("kajyou,mondai_no,rev,mondai,mondai_a,mondai_b,mondai_c,seikai,kaisetsu\n")
    csv.write("8.3,Q-1,-,Short?,same,same,C,d,short\n")
    csv.rewind

    report = TestmondaiQualityAuditService.call([csv.path])

    assert_equal 1, report[:scanned_files]
    assert_equal 1, report[:files].first[:row_count]
    assert report[:files].first[:issues].any? { |issue| issue[:type] == 'duplicate_choices' }
    assert report[:files].first[:issues].any? { |issue| issue[:type] == 'invalid_seikai' }
    assert report[:files].first[:issues].any? { |issue| issue[:type] == 'short_explanation' }
  ensure
    csv.close!
  end

  test 'detects mojibake like text patterns' do
    csv = Tempfile.new(['audit_mojibake', '.csv'])
    csv.write("kajyou,mondai_no,rev,mondai,mondai_a,mondai_b,mondai_c,seikai,kaisetsu\n")
    csv.write("8.3,Q-2,REV1,險ｭ險井ｻ墓ｧ俶嶌,a,b,c,a,縺薙ｌ縺ｯ解説です\n")
    csv.rewind

    report = TestmondaiQualityAuditService.call([csv.path])

    assert report[:files].first[:issues].any? { |issue| issue[:type] == 'mojibake_suspected' }
  ensure
    csv.close!
  end

  test 'accepts headerless 9-column quiz csv' do
    csv = Tempfile.new(['kajyou_audit_headerless', '.csv'])
    csv.write("8.3,1,-,Question text long enough,Choice A,Choice B,Choice C,a,Explanation text long enough\n")
    csv.write("8.3,2,-,Another question long enough,Choice A,Choice B,Choice C,b,Another explanation long enough\n")
    csv.rewind

    report = TestmondaiQualityAuditService.call([csv.path])

    assert_equal 1, report[:scanned_files]
    assert_equal 2, report[:files].first[:row_count]
  ensure
    csv.close!
  end

  test 'skips non quiz csv instead of raising parse_error' do
    csv = Tempfile.new(['audit_non_quiz', '.csv'])
    csv.write("filename,category,status\n")
    csv.write("sample.pdf,docs,open\n")
    csv.rewind

    report = TestmondaiQualityAuditService.call([csv.path])

    assert_equal 0, report[:scanned_files]
    assert_equal 1, report[:skipped_files]
    assert_equal 'not_quiz_csv', report[:skipped].first[:reason]
  ensure
    csv.close!
  end
end
