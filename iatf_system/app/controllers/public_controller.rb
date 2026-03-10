# frozen_string_literal: true

class PublicController < ApplicationController
  def favicon
    send_file 'public/favicon.ico', type: 'image/x-icon', disposition: 'inline'
  end

  def robots
    send_file 'public/robots.txt', type: 'text/plain', disposition: 'inline'
  end
end
