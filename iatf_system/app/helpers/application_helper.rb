# frozen_string_literal: true

module ApplicationHelper
  def icon_for_extension(ext)
    case ext
    when '.xls', '.xlsx', '.xlsm'
      'excel.png'
    when '.pdf'
      'pdf.png'
    when '.ppt', '.pptx'
      'ppt.png'
    when '.jpg'
      'jpg.png'
    when '.png'
      'png.png'
    when '.dxf'
      'dxf.png'
    when '.html'
      'html.png'
    when '.accdb'
      'access.png'
    when '.doc', '.docx'
      'word.png'
    when '.zip'
      'zip.png'
    when '.stp', '.stl', '.step', '.igs', '.iges'
      '3dcad.png'
    when '.dwg'
      'dwg.png'
    when '.mp4'
      'mp4.png'
    else
      'default.png' # デフォルトのアイコンを追加
    end
  end

  def bootstrap_class_for(flash_type)
    {
      success: 'alert-success',
      error: 'alert-danger',
      alert: 'alert-warning',
      notice: 'alert-info'
    }[flash_type.to_sym] || flash_type.to_s
  end
end
