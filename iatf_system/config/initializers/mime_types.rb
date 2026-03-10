# frozen_string_literal: true

# Be sure to restart your server when you modify this file.

# Add new mime types for use in respond_to blocks:
# Mime::Type.register "text/richtext", :rtf

# RailsでAxlsxを使ってxlsxを生成
# https://qiita.com/necojackarc/items/0dbd672b2888c30c5a38

Mime::Type.unregister :xlsx
Mime::Type.register 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', :xlsx
