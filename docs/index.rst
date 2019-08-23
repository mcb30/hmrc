HMRC API client library
=======================

The United Kingdom tax authority (HMRC) provides a set of `RESTful
APIs <https://developer.service.hmrc.gov.uk/api-documentation>`_ for
managing tax affairs.  These APIs can be used to view tax accounts,
submit tax returns, confirm receipt of payments, and so forth.

As of April 2019, use of these APIs is `mandatory for Value Added Tax
(VAT)
<https://www.gov.uk/government/publications/vat-notice-70022-making-tax-digital-for-vat>`_.
There is no longer any way for most taxpayers to submit VAT returns
via the HMRC web site.

A VAT return submitted via the VAT API is essentially a JSON
representation of the HTML form previously used on the HMRC web site
(which itself was simply a transcription of the old paper VAT100
form).  For example:

.. code-block:: json

   {
     "periodKey": "A001",
     "vatDueSales": 105.50,
     "vatDueAcquisitions": -100.45,
     "totalVatDue": 5.05,
     "vatReclaimedCurrPeriod": 105.15,
     "netVatDue": 100.10,
     "totalValueSalesExVAT": 300,
     "totalValuePurchasesExVAT": 300,
     "totalValueGoodsSuppliedExVAT": 3000,
     "totalAcquisitionsExVAT": 3000,
     "finalised": true
   }

This JSON representation is submitted via HTTP POST to the VAT
submission endpoint at
``https://api.service.hmrc.gov.uk/organisations/vat/{vrn}/returns``.
Other endpoints allow for retrieving the list of open and fulfilled
VAT returns, for retrieving the details of an already-submitted VAT
return, and for viewing payments received by HMRC.

The :mod:`hmrc` module can be used to interact with the HMRC APIs in a
Pythonic way.  For example:

.. code-block:: python

   >>> from datetime import date
   >>> from hmrc.auth import HmrcSession, browser_auth
   >>> from hmrc.api.vat import VatClient, VatObligationStatus

   >>> session = HmrcSession(client_id, client_secret=client_secret,
   ...                       auto_auth=browser_auth)
   >>> vat = VatClient(session, vrn='195036945')
   >>> session.authorize()
   Please enter the code obtained via the browser:
   c333790c9c4f4a8a97501f339a6f4954

   >>> start = date(2018, 1, 1)
   >>> end = date(2018, 12, 31)
   >>> obligations = vat.obligations(from_=start, to=end)
   >>> print(obligations)
   VatObligations(obligations=[VatObligation(start=..., ...), ...])

   >>> fulfilled = [x for x in obligations.obligations
   ...              if x.status == VatObligationStatus.FULFILLED]

   >>> print(vat.retrieve(period_key=fulfilled[0].period_key))

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules/hmrc

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
