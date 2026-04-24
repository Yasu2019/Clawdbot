# frozen_string_literal: true

module ApplicationHelper
  def global_back_href
    # touans/index は常に TOP (products_path / root_path) へ戻るようにする
    if controller_name == 'touans' && action_name == 'index'
      return products_path if respond_to?(:products_path) && respond_to?(:user_signed_in?) && user_signed_in?
      return root_path
    end

    referer = request&.referer.to_s
    current = request&.url.to_s

    if referer.present?
      begin
        ref_uri = URI.parse(referer)
        curr_uri = URI.parse(current)

        # パスが同じ場合（パラメータ違い等）は戻り先として扱わず、フォールバックさせる
        if ref_uri.host != curr_uri.host || ref_uri.path != curr_uri.path
          return referer
        end
      rescue URI::InvalidURIError
        return referer if referer != current
      end
    end

    if respond_to?(:products_path) && respond_to?(:user_signed_in?) && user_signed_in?
      return products_path
    end

    root_path
  rescue StandardError
    root_path
  end

  def show_global_back_button?
    return false if controller_name == "suppliers" && action_name == "index"
    return false if controller_name == "products" && action_name == "index"

    !devise_controller?
  rescue StandardError
    true
  end

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
      'other.png'
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
