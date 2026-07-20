// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

/* eslint-disable react/no-unescaped-entities */
'use client';

import Link from 'next/link';

export default function RefundPolicyPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] py-16">
      <div className="container mx-auto max-w-4xl px-4">
        {/* Header */}
        <div className="mb-16 text-center">
          <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-r from-green-500/20 to-emerald-500/20">
            <svg
              className="h-8 w-8 text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h1 className="mb-4 bg-gradient-to-r from-white via-gray-100 to-gray-300 bg-clip-text font-bold text-4xl text-transparent">
            Refund Policy
          </h1>
          <p className="text-gray-400 text-lg">
            Understanding our refund and cancellation procedures
          </p>
          <p className="mt-2 text-gray-500 text-sm">Last updated: September 10, 2025</p>
        </div>

        {/* Content */}
        <div className="prose prose-invert max-w-none">
          <div className="space-y-8 rounded-2xl border border-gray-800/50 bg-gray-900/50 p-8 backdrop-blur-xl">
            {/* Introduction */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                1. Introduction
              </h2>
              <p className="mb-4 text-gray-300 leading-relaxed">
                At Exiqus, we want you to be completely satisfied with our AI-powered developer
                assessment platform. This Refund Policy explains the circumstances under which
                refunds are available and the process for requesting them.
              </p>
              <p className="text-gray-300 leading-relaxed">
                This policy applies to all subscription plans and services offered by Exiqus. By
                subscribing to our services, you acknowledge and agree to the terms outlined in this
                Refund Policy.
              </p>
            </section>

            {/* Satisfaction Guarantee */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                2. 30-Day Satisfaction Guarantee
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                We offer a 30-day satisfaction guarantee for new subscribers to any paid plan:
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">2.1 Eligibility Criteria</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>First-time subscribers to any paid Exiqus plan</li>
                <li>Refund request submitted within 30 days of initial subscription</li>
                <li>Account in good standing with no violations of our Terms of Service</li>
                <li>Reasonable usage of the service (not excessive or abusive)</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">2.2 What's Covered</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Full refund of the first month's subscription fee</li>
                <li>Pro-rated refund for annual subscriptions within the 30-day period</li>
                <li>Cancellation of recurring billing</li>
                <li>Retention of analysis data for 30 days post-cancellation</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">2.3 What's Not Covered</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Add-on services or overages beyond base subscription</li>
                <li>Third-party integrations or services</li>
                <li>API usage fees above included quota</li>
                <li>Priority support fees (if applicable)</li>
              </ul>
            </section>

            {/* Subscription-Specific Policies */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                3. Subscription-Specific Policies
              </h2>

              <h3 className="mb-3 font-semibold text-white text-xl">3.1 Free Plan</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Our Free plan has no refund considerations as it involves no payment. Users may
                cancel at any time without notice.
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">
                3.2 Starter Plan ($49/month)
              </h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>30-day satisfaction guarantee applies</li>
                <li>Monthly subscriptions: Full refund if canceled within 30 days</li>
                <li>No partial month refunds after 30-day period</li>
                <li>Cancel anytime, service continues until end of billing period</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">
                3.3 Growth Plan ($199/month)
              </h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>30-day satisfaction guarantee applies</li>
                <li>Priority support services are non-refundable after use</li>
                <li>Unused analysis credits do not carry over or receive refunds</li>
                <li>API key usage fees are non-refundable</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">3.4 Scale Plan ($499/month)</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>30-day satisfaction guarantee applies</li>
                <li>Batch analysis processing fees are non-refundable once initiated</li>
                <li>Custom integrations (if any) are non-refundable</li>
                <li>Advanced features usage is non-refundable</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">
                3.5 Scale+ Plan (Custom Pricing)
              </h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>30-day satisfaction guarantee applies</li>
                <li>Dedicated support hours are non-refundable once used</li>
                <li>Custom reporting features are non-refundable</li>
                <li>Advanced API usage is non-refundable</li>
              </ul>
            </section>

            {/* Cancellation Process */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                4. Cancellation Process
              </h2>

              <h3 className="mb-3 font-semibold text-white text-xl">
                4.1 Contact Support for Cancellation
              </h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                To cancel your subscription, please contact our support team:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Use the in-app contact form</li>
                <li>
                  Use our{' '}
                  <Link href="/contact" className="text-indigo-400 underline hover:text-indigo-300">
                    contact form
                  </Link>
                </li>
                <li>Priority support users: Use your dedicated channel</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">4.2 Effective Date</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Cancellations take effect at the end of your current billing period unless you
                request an immediate cancellation for refund purposes within the 30-day guarantee
                period.
              </p>
            </section>

            {/* Refund Request Process */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                5. Refund Request Process
              </h2>

              <h3 className="mb-3 font-semibold text-white text-xl">5.1 How to Request a Refund</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                To request a refund under our 30-day satisfaction guarantee:
              </p>
              <ol className="mb-4 ml-4 list-inside list-decimal space-y-1 text-gray-300">
                <li>Contact our support team within 30 days of your initial subscription</li>
                <li>Provide your account email and subscription details</li>
                <li>Briefly explain your reason for requesting a refund</li>
                <li>Allow us to address any concerns or technical issues first</li>
                <li>If resolution isn't possible, we'll process your refund request</li>
              </ol>

              <h3 className="mb-3 font-semibold text-white text-xl">5.2 Processing Timeline</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Refund requests are reviewed within 2 business days</li>
                <li>Approved refunds are processed within 5-10 business days</li>
                <li>Refunds appear on your original payment method</li>
                <li>You'll receive email confirmation once processed</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">5.3 Required Information</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Please provide the following when requesting a refund:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Account email address</li>
                <li>Subscription plan and billing date</li>
                <li>Transaction ID or invoice number (if available)</li>
                <li>Reason for refund request</li>
                <li>Any specific issues or concerns experienced</li>
              </ul>
            </section>

            {/* Exceptions and Special Circumstances */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                6. Exceptions and Special Circumstances
              </h2>

              <h3 className="mb-3 font-semibold text-white text-xl">6.1 Service Outages</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                In case of extended service outages affecting your ability to use Exiqus:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Service credits will be applied for downtime exceeding 4 hours</li>
                <li>Credits are calculated as a percentage of your monthly subscription</li>
                <li>Credits are automatically applied to your next billing cycle</li>
                <li>No action required from users for standard service credits</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">6.2 Technical Issues</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                For platform-related technical issues preventing service use:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Our support team will first attempt to resolve the issue</li>
                <li>If resolution isn't possible, refund consideration may apply</li>
                <li>Evaluation on a case-by-case basis</li>
                <li>Documentation of the issue may be required</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">6.3 Fraudulent Activities</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Accounts involved in fraudulent activities are not eligible for refunds:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Abuse of the platform or services</li>
                <li>Violation of Terms of Service</li>
                <li>Chargeback abuse or payment disputes</li>
                <li>Creation of multiple accounts to abuse trial periods</li>
              </ul>
            </section>

            {/* Annual Subscriptions */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                7. Annual Subscriptions
              </h2>

              <h3 className="mb-3 font-semibold text-white text-xl">7.1 Refund Policy</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Annual subscriptions receive special treatment under our refund policy:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>30-day satisfaction guarantee applies to the full annual amount</li>
                <li>After 30 days, no refunds are available for unused months</li>
                <li>Service continues until the end of the annual term</li>
                <li>Annual subscribers receive priority consideration for service credits</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">
                7.2 Pro-Rated Considerations
              </h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                In exceptional circumstances, we may offer pro-rated refunds for annual
                subscriptions:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Significant changes to service terms or features</li>
                <li>Extended service unavailability</li>
                <li>Technical issues preventing service use</li>
                <li>Evaluation on a case-by-case basis</li>
              </ul>
            </section>

            {/* Data Retention After Cancellation */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                8. Data Retention After Cancellation
              </h2>

              <h3 className="mb-3 font-semibold text-white text-xl">8.1 Grace Period</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                After cancellation, we provide a 30-day grace period:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Analysis data remains accessible for 30 days</li>
                <li>Account data is preserved for potential reactivation</li>
                <li>No new analyses can be performed during this period</li>
                <li>Data export is available during the grace period</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">8.2 Data Deletion</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">After the 30-day grace period:</p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Analysis data may be permanently deleted</li>
                <li>Account information is anonymized or deleted</li>
                <li>Billing records are retained for accounting purposes</li>
                <li>Legal compliance data is retained as required</li>
              </ul>
            </section>

            {/* Payment Method Issues */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                9. Payment Method Issues
              </h2>

              <h3 className="mb-3 font-semibold text-white text-xl">9.1 Failed Payments</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                When payments fail, we follow this process:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Multiple retry attempts over several days</li>
                <li>Email notifications to update payment information</li>
                <li>Account downgrade after 7 days of failed payments</li>
                <li>Service suspension after 14 days</li>
                <li>Account cancellation after 30 days</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">
                9.2 Chargebacks and Disputes
              </h3>
              <p className="mb-4 text-gray-300 leading-relaxed">For payment disputes:</p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Contact us directly before initiating chargebacks</li>
                <li>We're committed to resolving billing issues quickly</li>
                <li>Chargebacks may result in account suspension</li>
                <li>Additional fees may apply for chargeback processing</li>
              </ul>
            </section>

            {/* Contact Information */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                10. Contact Us
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                For refund requests, cancellations, or questions about this policy:
              </p>

              <div className="space-y-2 rounded-lg bg-gray-800/30 p-4">
                <p className="text-gray-300">
                  <span className="font-semibold text-white">Billing Support:</span> the contact
                  form
                </p>
                <p className="text-gray-300">
                  <span className="font-semibold text-white">General Support:</span> the contact
                  form
                </p>
                <p className="text-gray-300">
                  <span className="font-semibold text-white">Contact Form:</span>{' '}
                  <Link href="/contact" className="text-indigo-400 underline hover:text-indigo-300">
                    Submit a Request
                  </Link>
                </p>
              </div>

              <p className="mt-4 text-gray-400 text-sm">
                For billing-related inquiries, please allow up to 2 business days for a response.
                For urgent refund requests, please mark your email as "URGENT REFUND REQUEST."
              </p>
            </section>

            {/* Changes to This Policy */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                11. Changes to This Refund Policy
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                We may update this Refund Policy from time to time. Changes will be communicated by:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Posting the updated policy on our website</li>
                <li>Updating the "Last updated" date</li>
                <li>Email notifications for significant changes</li>
                <li>In-app notifications when appropriate</li>
              </ul>

              <p className="text-gray-300 leading-relaxed">
                Changes to this policy will not affect refund requests submitted before the
                effective date of the changes.
              </p>
            </section>

            {/* Related Links */}
            <section className="border-gray-700/50 border-t pt-8">
              <h2 className="mb-4 font-bold text-white text-xl">Related Legal Documents</h2>
              <div className="flex flex-wrap gap-4">
                <Link
                  href="/terms"
                  className="inline-flex items-center rounded-lg bg-gray-800/50 px-4 py-2 text-indigo-400 transition-all duration-200 hover:bg-gray-800 hover:text-indigo-300"
                >
                  Terms of Service
                </Link>
                <Link
                  href="/privacy"
                  className="inline-flex items-center rounded-lg bg-gray-800/50 px-4 py-2 text-indigo-400 transition-all duration-200 hover:bg-gray-800 hover:text-indigo-300"
                >
                  Privacy Policy
                </Link>
                <Link
                  href="/contact"
                  className="inline-flex items-center rounded-lg bg-gray-800/50 px-4 py-2 text-indigo-400 transition-all duration-200 hover:bg-gray-800 hover:text-indigo-300"
                >
                  Contact Us
                </Link>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
