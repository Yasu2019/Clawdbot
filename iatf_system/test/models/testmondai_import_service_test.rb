# frozen_string_literal: true

require 'test_helper'
require 'tempfile'

class TestmondaiImportServiceTest < ActiveSupport::TestCase
  test 'imports rows using business key when id is not present' do
    csv = Tempfile.new(['testmondai', '.csv'])
    csv.write("kajyou,mondai_no,rev,mondai,mondai_a,mondai_b,mondai_c,seikai,kaisetsu\n")
    csv.write("8.5,Q-100,REV1,Question,A,B,C,a,Explanation\n")
    csv.rewind

    result = TestmondaiImportService.call(csv)

    assert result.success?
    record = Testmondai.find_by(kajyou: '8.5', mondai_no: 'Q-100', rev: 'REV1')
    assert_not_nil record
    assert_equal 'Question', record.mondai
  ensure
    csv.close!
  end

  test 'reports missing required columns' do
    csv = Tempfile.new(['testmondai_bad', '.csv'])
    csv.write("kajyou,mondai_no,mondai\n")
    csv.write("8.5,Q-100,Question\n")
    csv.rewind

    result = TestmondaiImportService.call(csv)

    assert_not result.success?
    assert_match(/Missing required columns/, result.errors.first)
  ensure
    csv.close!
  end

  test 'imports headerless 9-column quiz rows' do
    csv = Tempfile.new(['kajyou_headerless_import', '.csv'])
    csv.write("8.5,Q-200,REV2,Question text long enough,Choice A,Choice B,Choice C,b,Explanation text long enough\n")
    csv.rewind

    result = TestmondaiImportService.call(csv)

    assert result.success?
    record = Testmondai.find_by(kajyou: '8.5', mondai_no: 'Q-200', rev: 'REV2')
    assert_not_nil record
    assert_equal 'b', record.seikai
  ensure
    csv.close!
  end

  test 'rejects rows with blank required quiz fields' do
    csv = Tempfile.new(['kajyou_blank_import', '.csv'])
    csv.write("kajyou,mondai_no,rev,mondai,mondai_a,mondai_b,mondai_c,seikai,kaisetsu\n")
    csv.write("8.5,Q-201,REV1,,A,B,C,a,Explanation\n")
    csv.rewind

    result = TestmondaiImportService.call(csv)

    assert_not result.success?
    assert_match(/required quiz fields are blank/, result.errors.first)
  ensure
    csv.close!
  end
end
